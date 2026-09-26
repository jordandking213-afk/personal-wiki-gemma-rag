"""Retrieval tool: BM25 keyword search over passages from the ORIGINAL raw notes.

It only finds evidence; it never generates text and never needs the model running.
"""
import json
import math
import re
from collections import Counter

from . import config
from .passages import all_passages

STOPWORDS = set("""
a an and are as at be but by can could couldn't did do does for from had has have he her
him his how i if in into is it its me my not of on or our she so than that the their them
then there these they this those to up us was we were what when where which who why will
with would you your about does doesn't dont don't just also only than too very one own
""".split())


def tokenize(text):
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower().replace("’", "'"))
    out = []
    for w in words:
        if w in STOPWORDS:
            continue
        # light stemming so "groans"/"groan", "sacrifices"/"sacrifice" match
        for suf in ("ing", "es", "s"):
            if len(w) > 4 and w.endswith(suf) and not w.endswith("ss"):
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


def build_index():
    passages = all_passages()
    docs = [tokenize(p["section"] + " " + p["text"]) for p in passages]
    df = Counter(t for d in docs for t in set(d))
    index = {
        "passages": passages,
        "doc_tokens": docs,
        "df": df,
        "avgdl": sum(map(len, docs)) / max(len(docs), 1),
    }
    config.DATA.mkdir(exist_ok=True)
    config.SEARCH_INDEX.write_text(json.dumps(index, indent=1, ensure_ascii=False))
    return index


def load_index():
    if not config.SEARCH_INDEX.exists():
        return build_index()
    return json.loads(config.SEARCH_INDEX.read_text())


def search(query, k=config.TOP_K, k1=1.5, b=0.75):
    """Return the top-k passages with BM25 scores (score > 0 only)."""
    index = load_index()
    n = len(index["passages"])
    q = tokenize(query)
    results = []
    for p, doc in zip(index["passages"], index["doc_tokens"]):
        tf = Counter(doc)
        score = 0.0
        for t in q:
            if t not in tf:
                continue
            df = index["df"].get(t, 0)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(doc) / index["avgdl"]))
        if score > 0:
            results.append({**p, "score": round(score, 3)})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]


def format_sources(results):
    """Numbered SOURCES block for prompts: [S1] path — section, then the passage text."""
    blocks = []
    for i, r in enumerate(results, 1):
        blocks.append(f"[S{i}] {r['source_path']} — {r['section']}\n{r['text']}")
    return "\n\n".join(blocks)
