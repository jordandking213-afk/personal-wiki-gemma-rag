"""Saved outputs: every search, ask, and chat run is written to evidence/<mode>/ as Markdown
(readable on GitHub) plus JSON (exact record), labeled with mode and local execution."""
import json
import re
from datetime import datetime

from . import config


def _stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _slug(text, n=6):
    return "-".join(re.findall(r"[a-z0-9]+", text.lower())[:n]) or "run"


def save(mode, title, record, markdown):
    folder = config.EVIDENCE / mode
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / f"{_stamp()}-{_slug(title)}"
    base.with_suffix(".json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
    base.with_suffix(".md").write_text(markdown)
    return base.with_suffix(".md")


def passages_md(results):
    if not results:
        return "_No passages matched._\n"
    out = []
    for i, r in enumerate(results, 1):
        body = "\n".join("> " + line for line in r["text"].splitlines())
        out.append(f"**[S{i}]** `{r['source_path']}` — {r['section']} (BM25 {r['score']})\n\n{body}\n")
    return "\n".join(out)


class ChatTranscript:
    """Appends each chat turn to one Markdown file for the session."""

    def __init__(self, info):
        folder = config.EVIDENCE / "chat"
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / f"{_stamp()}-chat-session.md"
        self.path.write_text(
            f"# Chat transcript\n\n- Mode: **chat** · Execution: **{info['execution']}**\n"
            f"- Model: `{info['model']}` · Runtime: {info['runtime']}\n"
            f"- Started: {datetime.now().isoformat(timespec='seconds')}\n")

    def add(self, user, reply, decision, results, check, stats):
        lines = [f"\n---\n\n**You:** {user}\n",
                 f"_Harness: {decision}_\n"]
        if results:
            lines.append("<details><summary>Notes retrieved</summary>\n\n" + passages_md(results) + "\n</details>\n")
        lines.append(f"**Assistant:**\n\n{reply}\n")
        if check:
            lines.append(f"_Citation check: {check}_ · _{stats['wall_seconds']}s_\n")
        else:
            lines.append(f"_{stats['wall_seconds']}s_\n")
        with self.path.open("a") as f:
            f.write("\n".join(lines))
