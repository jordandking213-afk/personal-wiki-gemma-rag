"""The three interaction modes. The harness enforces their differences:

search: retrieval tool only. Returns original passages; never calls the model.
ask:    RAG. Retrieve -> research rules + numbered SOURCES -> local Gemma -> citation check.
        Standalone: no chat history, no persona.
chat:   persona + recent conversation. Retrieves notes only when the turn needs them.
"""
import re
from datetime import datetime

from . import config, evidence, llm, retrieval

INSUFFICIENT = "INSUFFICIENT EVIDENCE"


# ---------- shared ----------

def check_citations(answer, n_sources, require=True):
    """Verify [S#] citations point at sources that were actually provided."""
    groups = re.findall(r"\[(S\d+(?:\s*[,;]\s*S?\d+)*)\]", answer)  # [S1], [S1, S4], [S1; S2]
    cited = sorted({int(x) for g in groups for x in re.findall(r"\d+", g)})
    invalid = [c for c in cited if not 1 <= c <= n_sources]
    insufficient = answer.strip().upper().startswith(INSUFFICIENT)
    if invalid:
        status = f"FAIL — cites sources that were not provided: {', '.join(f'S{c}' for c in invalid)}"
    elif insufficient:
        status = "OK — insufficient-evidence response" + (f" (mentions {', '.join(f'S{c}' for c in cited)})" if cited else "")
    elif not cited and require:
        status = "FAIL — answer makes claims without any citation"
    elif not cited:
        status = "no citations (none needed)"
    else:
        status = f"OK — cites {', '.join(f'S{c}' for c in cited)}, all provided"
    return {"cited": cited, "invalid": invalid, "insufficient": insufficient, "status": status}


def citation_legend(results, cited):
    return [f"  [S{i}] {r['source_path']} — {r['section'][-80:]}"
            for i, r in enumerate(results, 1) if i in cited]


def header(mode):
    model = "none (retrieval only)" if mode == "search" else config.MODEL
    return f"── {mode} · execution: local · model: {model} ──"


# ---------- search ----------

def run_search(query, k=5, save=True):
    results = retrieval.search(query, k=k)
    print(header("search"))
    if not results:
        print("No passages matched. Try different words.")
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r['source_path']}  (BM25 {r['score']})\n    section: {r['section']}")
        for line in r["text"].splitlines():
            print("    │ " + line)
    if save:
        md = (f"# Search: {query}\n\n- Mode: **search** (retrieval only, no model call) · Execution: **local**\n"
              f"- Time: {datetime.now().isoformat(timespec='seconds')}\n\n" + evidence.passages_md(results))
        path = evidence.save("search", query, {"mode": "search", "query": query, "results": results}, md)
        print(f"\nsaved: {path.relative_to(config.ROOT)}")
    return results


# ---------- ask ----------

def run_ask(question, save=True):
    print(header("ask") + "  (standalone RAG, no chat history)")
    results = retrieval.search(question, k=config.TOP_K)
    rules = config.RESEARCH_RULES.read_text()
    print(f"retrieved {len(results)} passages: " + ", ".join(f"S{i}={r['id']}" for i, r in enumerate(results, 1)))

    if not results:
        # Nothing matched at all: the harness answers without calling the model.
        answer, stats = f"{INSUFFICIENT}: The study notes do not contain this information.", {"wall_seconds": 0, "model_called": False}
    else:
        prompt = f"SOURCES:\n\n{retrieval.format_sources(results)}\n\nQUESTION: {question}"
        messages = [{"role": "system", "content": rules}, {"role": "user", "content": prompt}]
        print()
        answer, stats = llm.chat(messages, temperature=0.1, on_token=lambda t: print(t, end="", flush=True))
        print()
        stats["model_called"] = True

    check = check_citations(answer, len(results))
    print("\nCitations:")
    print("\n".join(citation_legend(results, check["cited"])) or "  (none)")
    print(f"Citation check: {check['status']}")
    print(f"Response time: {stats['wall_seconds']}s" + (f" (model load {stats['load_seconds']}s)" if stats.get("load_seconds") else ""))

    record = {"mode": "ask", "question": question, **llm.model_info(),
              "time": datetime.now().isoformat(timespec="seconds"),
              "retrieved": results, "answer": answer, "citation_check": check, "stats": stats,
              "memory": llm.memory_snapshot()}
    if save:
        md = (f"# Ask: {question}\n\n"
              f"- Mode: **ask** (standalone, no chat history) · Execution: **local**\n"
              f"- Model: `{config.MODEL}` · Runtime: {record['runtime']} · Time: {record['time']}\n"
              f"- Response time: {stats['wall_seconds']}s · Memory: {record['memory']}\n\n"
              f"## Retrieved passages\n\n{evidence.passages_md(results)}\n"
              f"## Gemma's answer\n\n{answer}\n\n"
              f"## Citation check\n\n{check['status']}\n")
        path = evidence.save("ask", question, record, md)
        print(f"saved: {path.relative_to(config.ROOT)}")
    return record


# ---------- chat ----------

# Turns that are about the conversation or the assistant itself never trigger a notes lookup.
CONVERSATIONAL = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank you|ok|okay|good (morning|evening|night))\b"
    r"|how (are|was|is) (you|your)\b|what can (you|we|i)\b|help me with\??\s*$|what do you do|who are you|how do(es)? (this|you) work"
    r"|\b(make|keep) (that|it|this)\b|\b(shorter|longer|simpler|rephrase|reword|rewrite|another version|try again)\b",
    re.I,
)


def decide_retrieval(message):
    """Return (results, decision text). Chat looks up notes only when the turn needs them."""
    if message.startswith("/notes"):
        query = message[len("/notes"):].strip()
        return retrieval.search(query, k=config.TOP_K), f"notes lookup forced by /notes for '{query}'"
    if CONVERSATIONAL.search(message):
        return [], "no notes lookup (conversational turn or follow-up on the conversation)"
    results = retrieval.search(message, k=config.TOP_K)
    top = results[0]["score"] if results else 0
    if re.search(config.CHAT_STUDY_WORDS, message, re.I) and results:
        return results, "looked up notes (message refers to the study)"
    tokens = retrieval.tokenize(message)
    vocab = retrieval.load_index()["df"]
    overlap = sum(t in vocab for t in tokens) / max(len(tokens), 1)
    if overlap >= config.CHAT_MIN_VOCAB_OVERLAP and top >= config.CHAT_MIN_SCORE:
        return results, f"looked up notes ({overlap:.0%} of words appear in the notes, top BM25 {top})"
    return [], f"no notes lookup ({overlap:.0%} of words appear in the notes, top BM25 {top}; not about the notes)"


CHAT_HELP = """Chat commands:
  /notes <topic>  force a lookup in the study notes for this turn
  /reset          clear the conversation
  /exit           quit (Ctrl-D also works)"""


def run_chat(save=True):
    persona = config.PERSONA.read_text()
    history = []  # alternating user/assistant messages: conversation context, not evidence
    transcript = evidence.ChatTranscript(llm.model_info()) if save else None
    print(header("chat") + "\nRomans Study Companion. Type /help for commands, /exit to quit.")
    while True:
        try:
            message = input("\nyou › ").strip()
        except EOFError:
            print()
            break
        if not message:
            continue
        if message in ("/exit", "/quit"):
            break
        if message == "/help":
            print(CHAT_HELP)
            continue
        if message == "/reset":
            history = []
            print("(conversation cleared)")
            continue

        results, decision = decide_retrieval(message)
        print(f"  [{decision}]")
        user_content = message if not message.startswith("/notes") else message[len("/notes"):].strip()
        if results:
            user_content += ("\n\nNOTES (retrieved from the study notes this turn; cite them as [S#]):\n\n"
                             + retrieval.format_sources(results))
        system = persona + "\n\nNotes looked up this turn: " + ("yes, see NOTES in the message." if results else "none.")
        messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": user_content}]

        print("\ncompanion › ", end="", flush=True)
        reply, stats = llm.chat(messages, temperature=0.6, on_token=lambda t: print(t, end="", flush=True))
        print()
        check = None
        if results:
            c = check_citations(reply, len(results), require=False)
            check = c["status"]
            legend = citation_legend(results, c["cited"])
            if legend:
                print("  sources:\n" + "\n".join(legend))
            print(f"  [citation check: {check}]")

        history += [{"role": "user", "content": user_content}, {"role": "assistant", "content": reply}]
        history = history[-2 * config.CHAT_HISTORY_TURNS:]
        if transcript:
            transcript.add(message, reply, decision, results, check, stats)
    if transcript:
        print(f"transcript saved: {transcript.path.relative_to(config.ROOT)}")
