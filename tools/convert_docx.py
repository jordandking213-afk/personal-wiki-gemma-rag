"""One-time conversion of the Bible study .docx files into Markdown raw sources.

Why: .docx files carry author metadata and cannot be opened inside Obsidian, so the
shareable originals in vault/raw/ are word-for-word Markdown copies. Only formatting
changes: Word bullets become Markdown "- " bullets, indented by their list level.
Uses only the Python standard library (zipfile + xml), so it runs offline.

Usage: python3 tools/convert_docx.py <input.docx> <output.md>
"""
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def paragraphs(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    for p in root.iter(W + "p"):
        text = "".join(t.text or "" for t in p.iter(W + "t"))
        ilvl = p.find(f"{W}pPr/{W}numPr/{W}ilvl")
        level = int(ilvl.get(W + "val")) if ilvl is not None else None
        yield level, text


def to_markdown(docx_path):
    lines = []
    for level, text in paragraphs(docx_path):
        if level is None:
            lines.append(text)
        else:
            lines.append("    " * level + "- " + text)
    return "\n".join(lines).strip() + "\n"


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(dst, "w", encoding="utf-8") as f:
        f.write(to_markdown(src))
    print(f"wrote {dst}")
