"""Split raw study notes into passages that keep their source path and section.

The notes are outlines: a plain line starts a section, and "- " bullets nest under it by
indentation. A passage is one section (or, if the section is long, one of its child bullets
with its full breadcrumb), so each passage is a coherent idea with a traceable location.
"""
import re
from pathlib import Path

from . import config


class Node:
    def __init__(self, text, depth):
        self.text, self.depth, self.children = text, depth, []

    def lines(self, indent=0):
        out = ["    " * indent + ("- " if indent else "") + self.text] if indent else self.text.splitlines()
        for c in self.children:
            out += c.lines(indent + 1)
        return out

    def word_count(self):
        return len(" ".join(self.lines()).split())


def parse_outline(text):
    """Build a tree: plain lines are depth-0 section headings, bullets nest by indent."""
    roots, stack = [], []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = re.match(r"^( *)- (.*)$", raw)
        if m is None:
            node = Node(raw.strip(), 0)
            if roots and roots[-1].text and not roots[-1].children:
                # Consecutive plain lines ("Israel rejections" / "Reasons ...") form one section.
                prev = roots.pop()
                node.text = f"{prev.text}\n{node.text}"
            roots.append(node)
            stack = [node]
            continue
        depth = len(m.group(1)) // 4 + 1
        node = Node(m.group(2).strip(), depth)
        while stack and stack[-1].depth >= depth:
            stack.pop()
        if not stack:  # bullets before any heading
            stack = [Node("", 0)]
            roots.append(stack[0])
        stack[-1].children.append(node)
        stack.append(node)
    return roots


def _split(node, trail):
    """Yield (breadcrumb, text) pieces no longer than PASSAGE_MAX_WORDS where possible."""
    path = trail + [node.text.replace("\n", " — ")] if node.text else trail
    if node.word_count() <= config.PASSAGE_MAX_WORDS or not node.children:
        yield " > ".join(path), "\n".join(node.lines())
        return
    for child in node.children:
        yield from _split(child, path)


def passages_for_file(path: Path):
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(config.ROOT).as_posix()
    out = []
    for root in parse_outline(text):
        for section, body in _split(root, []):
            out.append({
                "id": f"{path.stem}#{len(out) + 1}",
                "source_path": rel,
                "source_title": path.stem,
                "section": section,
                "text": body,
            })
    return out


def all_passages():
    out = []
    for p in sorted(config.RAW_DIR.glob("*.md")):
        out += passages_for_file(p)
    return out
