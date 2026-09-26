"""Ingestion: raw study notes -> Gemma-organized, linked wiki pages + search index.

Flow per source:
  1. split the raw note into numbered passages (passages.py)
  2. Gemma proposes an overview + 3-5 topic notes, each tied to the passages it came from
  3. the harness cleans titles into short readable filenames and stores the structured
     content in data/pages.json (keyed by title, per source)
Then, across the whole wiki:
  4. Gemma picks related notes for each topic (only from titles that exist) with a reason
  5. the harness renders Markdown pages, index.md, the source catalog, and the search index

Re-ingesting a source that is already in data/manifest.json reuses its recorded titles,
so pages are updated in place instead of duplicated.
"""
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

from . import config, llm, retrieval
from .passages import passages_for_file

CHAPTERS = "Chapters"
CONCEPTS = "Concepts"

TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "topics": {
            "type": "array",
            "minItems": 3,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "key_points": {"type": "array", "items": {"type": "string"}},
                    "passages": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "summary", "key_points", "passages"],
            },
        },
    },
    "required": ["overview", "topics"],
}

LINK_SCHEMA = {
    "type": "object",
    "properties": {
        "related": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "why": {"type": "string"}},
                "required": ["title", "why"],
            },
        }
    },
    "required": ["related"],
}


# ---------- small helpers ----------

def _load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def source_id(path: Path):
    """Stable machine id kept in metadata, e.g. 'romans-08-study-notes'."""
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    return re.sub(r"romans-(\d)(?=-)", r"romans-0\1", slug)


def chapter_title(path: Path):
    return path.stem.replace("Study Notes", "Overview").strip()


SMALL = {"of", "and", "the", "in", "to", "a", "an", "as", "for", "on", "with", "by", "vs"}


def clean_title(raw, existing):
    """Short, readable, filename-safe title (2-6 words), reusing an existing title if it matches."""
    t = raw.replace("’", "'").replace("‘", "'")
    t = re.sub(r"'(?!s\b)", " ", t)  # keep possessive 's ("Israel's"), drop other quotes
    t = re.sub(r'[\[\]#^|:/\\?*"<>“”.,;!()]', " ", t)
    words = t.split()[:6]
    words = [w if (w.isupper() or any(c.isdigit() for c in w)) else
             (w.lower() if i and w.lower() in SMALL else w[:1].upper() + w[1:])
             for i, w in enumerate(words)]
    title = " ".join(words) or "Untitled Topic"
    for e in existing:
        if e.lower() == title.lower():
            return e
    return title


def first_sentence(text, limit=140):
    s = re.split(r"(?<=[.!?])\s", text.strip())[0]
    return s if len(s) <= limit else s[: limit - 1].rsplit(" ", 1)[0] + "…"


# ---------- Gemma steps ----------

def gemma_topics(src_path, passages, required_titles, other_titles):
    numbered = "\n\n".join(f"[P{i}] ({p['section']})\n{p['text']}" for i, p in enumerate(passages, 1))
    if required_titles:
        title_rule = ("This note was ingested before. Use EXACTLY these topic titles, one topic "
                      "each, and no others: " + "; ".join(required_titles))
    else:
        title_rule = ("Create 3 to 5 topics. Each title names one subject in 2 to 5 words, like "
                      "'Living Sacrifice' or 'Purpose of the Law'. No full sentences, no verse "
                      "numbers alone, no words like 'notes' or 'section'.")
        if other_titles:
            title_rule += (" If a topic is the same subject as one of these existing notes, reuse its "
                           "exact title: " + "; ".join(other_titles))
    prompt = f"""You are organizing a personal Bible study wiki. Below are numbered passages from the study note "{src_path.stem}".

{numbered}

Task: write an overview of the whole note and organize it into topic notes.
- overview: 2-3 sentences describing what this study note covers.
- {title_rule}
- summary: 1-2 sentences describing the topic, using only what the passages say.
- key_points: 2-5 short points restating what the passages say. Do not add facts, verses, or interpretations that are not in the passages.
- passages: the passage labels (like "P2") that the topic comes from.
Respond with JSON only."""
    text, stats = llm.chat([{"role": "user", "content": prompt}], temperature=0.2, json_schema=TOPIC_SCHEMA)
    return json.loads(text), stats


GAP_SCHEMA = {
    "type": "object",
    "properties": {"topics": {**TOPIC_SCHEMA["properties"]["topics"], "minItems": 1, "maxItems": 2}},
    "required": ["topics"],
}


def gemma_gap_topics(src_path, passages, uncovered, existing_titles):
    """Coverage check follow-up: ask Gemma for topics covering passages no topic used."""
    numbered = "\n\n".join(f"[P{i}] ({passages[i - 1]['section']})\n{passages[i - 1]['text']}" for i in uncovered)
    prompt = f"""You are organizing a personal Bible study wiki. These passages from the study note "{src_path.stem}" are not yet covered by any wiki note:

{numbered}

Existing notes (do not repeat these subjects): {"; ".join(existing_titles)}

Create 1 or 2 new topic notes that cover these passages.
- title: names one subject in 2 to 5 words. No full sentences.
- summary: 1-2 sentences using only what the passages say.
- key_points: 2-5 short points restating what the passages say. Do not add facts, verses, or interpretations that are not in the passages.
- passages: the passage labels (like "P2") the topic comes from.
Respond with JSON only."""
    text, stats = llm.chat([{"role": "user", "content": prompt}], temperature=0.2, json_schema=GAP_SCHEMA)
    return json.loads(text)["topics"], stats


def passage_numbers(labels, count):
    return [int(x) for x in re.findall(r"\d+", " ".join(labels)) if 0 < int(x) <= count]


def gemma_links(title, summary, candidates):
    listing = "\n".join(f"- {t}: {s}" for t, s in candidates)
    prompt = f"""A Bible study wiki has a note titled "{title}".
Summary: {summary}

Other notes in the wiki:
{listing}

Choose up to 3 other notes that are genuinely related to "{title}" (same idea, cause and effect, contrast, or one applies the other). For each, give a one-sentence reason a reader should follow the link. If none are truly related, return an empty list. Use exact titles from the list. Respond with JSON only."""
    text, stats = llm.chat([{"role": "user", "content": prompt}], temperature=0.2, json_schema=LINK_SCHEMA)
    return json.loads(text).get("related", []), stats


# ---------- rendering ----------

def _frontmatter(fields):
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f'  - "{x}"' for x in v]
        else:
            lines.append(f"{k}: {json.dumps(v) if isinstance(v, str) else v}")
    return "\n".join(lines + ["---", ""])


def render_concept(title, page, manifest):
    srcs = page["sources"]
    fm = _frontmatter({
        "title": title,
        "type": "concept",
        "source_ids": list(srcs),
        "source_files": [manifest[s]["raw_path"] for s in srcs],
        "generated_by": f"{config.MODEL} (local, Ollama)",
        "generated_at": page["generated_at"],
        "reviewed": page.get("reviewed", False),
    })
    out = [fm, f"# {title}", ""]
    out.append("## Summary")
    for sid, c in srcs.items():
        out.append(c["summary"] + (f" *(from [[{manifest[sid]['raw_title']}]])*" if len(srcs) > 1 else ""))
        out.append("")
    out.append("## Key Points")
    for sid, c in srcs.items():
        out += [f"- {kp}" for kp in c["key_points"]]
    out.append("")
    if page.get("related"):
        out.append("## Related Notes")
        out += [f"- [[{r['title']}]] — {r['why']}" for r in page["related"]]
        out.append("")
    out.append("## Sources")
    for sid, c in srcs.items():
        m = manifest[sid]
        out.append(f"- [[{m['raw_title']}]] (`{m['raw_path']}`), sections:")
        out += [f"    - {' > '.join(s.split(' > ')[-2:])}" for s in c["sections"]]
        out.append(f"- Chapter overview: [[{m['chapter']}]]")
    return "\n".join(out) + "\n"


def render_chapter(sid, m, pages):
    fm = _frontmatter({
        "title": m["chapter"],
        "type": "chapter",
        "source_ids": [sid],
        "source_files": [m["raw_path"]],
        "original_file": m["original_file"],
        "generated_by": f"{config.MODEL} (local, Ollama)",
        "generated_at": m["ingested_at"],
        "reviewed": m.get("reviewed", False),
    })
    out = [fm, f"# {m['chapter']}", "", m["overview"], "", "## Topics in This Chapter"]
    for t in m["topics"]:
        out.append(f"- [[{t}]] — {first_sentence(pages[t]['sources'][sid]['summary'])}")
    out += ["", "## Source", f"- Original study note: [[{m['raw_title']}]] (`{m['raw_path']}`)",
            "- Back to [[index]]"]
    return "\n".join(out) + "\n"


def render_index(manifest, pages):
    out = ["# Romans Study Wiki", "",
           "This serves as a guide that unpacks sections from Romans 8, 10, and 12 from the Bible.", "",
           "Start with a chapter overview, follow its topic links, and use each note's **Sources** "
           "section to get back to the original study notes.", "", "## Chapters"]
    for sid in sorted(manifest):
        m = manifest[sid]
        out.append(f"- [[{m['chapter']}]] — {first_sentence(m['overview'])}")
    for sid in sorted(manifest):
        m = manifest[sid]
        out += ["", f"## Topics from {m['chapter'].replace(' Overview', '')}"]
        for t in m["topics"]:
            out.append(f"- [[{t}]] — {first_sentence(pages[t]['sources'][sid]['summary'])}")
    out += ["", "## Original Sources",
            "- [[Source Catalog]] — where each original note came from and which pages it produced"]
    out += [f"- [[{manifest[s]['raw_title']}]]" for s in sorted(manifest)]
    return "\n".join(out) + "\n"


def render_catalog(manifest):
    out = ["# Source Catalog", "",
           "Original sources are stored unchanged in `raw/`. They were converted once from the "
           "author's Word documents to Markdown (same words, bullet formatting only) and had "
           "private prayer requests removed before being added to this vault.", "",
           "| Source ID | Raw note | Original file | SHA-256 (first 12) | Pages generated |",
           "|---|---|---|---|---|"]
    for sid in sorted(manifest):
        m = manifest[sid]
        pages = ", ".join(f"[[{t}]]" for t in [m["chapter"]] + m["topics"])
        out.append(f"| `{sid}` | [[{m['raw_title']}]] | {m['original_file']} | `{m['sha256'][:12]}` | {pages} |")
    out += ["", "Back to [[index]]"]
    return "\n".join(out) + "\n"


ORIGINAL_FILES = {  # raw note -> the Word document it was converted from
    "Romans 8 Study Notes": "Romans 8_18 - 30.docx",
    "Romans 10 Study Notes": "Romans 10.docx",
    "Romans 12 Study Notes": "Romans 12.docx",
}


def write_wiki(manifest, pages):
    concepts_dir, chapters_dir = config.WIKI_DIR / CONCEPTS, config.WIKI_DIR / CHAPTERS
    concepts_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    wanted = {concepts_dir / f"{t}.md" for t in pages} | {chapters_dir / f"{m['chapter']}.md" for m in manifest.values()}
    for f in list(concepts_dir.glob("*.md")) + list(chapters_dir.glob("*.md")):
        if f not in wanted:  # a title was renamed or merged: remove the stale page
            f.unlink()
    for t, page in pages.items():
        (concepts_dir / f"{t}.md").write_text(render_concept(t, page, manifest))
    for sid, m in manifest.items():
        (chapters_dir / f"{m['chapter']}.md").write_text(render_chapter(sid, m, pages))
    config.INDEX_MD.write_text(render_index(manifest, pages))
    config.CATALOG_MD.write_text(render_catalog(manifest))


# ---------- main entry ----------

def ingest(raw_path: Path, force=False, say=print):
    raw_path = Path(raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"No such file or folder: {raw_path}")
    files = sorted(raw_path.glob("*.md")) if raw_path.is_dir() else [raw_path]
    if not files:
        raise FileNotFoundError(f"No .md sources found in {raw_path}")

    manifest = _load(config.MANIFEST, {})
    pages = _load(config.PAGES, {})
    log = {"started": datetime.now().isoformat(timespec="seconds"), **llm.model_info(), "steps": []}
    t0 = time.time()
    changed = False

    for f in files:
        f = f.resolve()
        sid = source_id(f)
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        prev = manifest.get(sid)
        if prev and prev["sha256"] == sha and not force:
            say(f"  = {f.name}: unchanged, pages kept ({len(prev['topics'])} topics)")
            continue

        passages = passages_for_file(f)
        required = prev["topics"] if prev else []
        others = [t for t in pages if not (prev and t in prev["topics"])]
        say(f"  > {f.name}: {len(passages)} passages -> asking Gemma for topics"
            + (" (reusing existing titles)" if required else ""))
        data, stats = gemma_topics(f, passages, required, others)
        log["steps"].append({"step": "topics", "source": sid, **stats, **llm.memory_snapshot()})

        # Coverage check: every passage should feed at least one topic note.
        covered = {n for t in data["topics"] for n in passage_numbers(t["passages"], len(passages))}
        uncovered = [i for i in range(1, len(passages) + 1) if i not in covered]
        if uncovered and not required:
            say(f"      coverage check: passages {', '.join(f'P{i}' for i in uncovered)} unused -> asking Gemma for gap topics")
            extra, stats = gemma_gap_topics(f, passages, uncovered, [t["title"] for t in data["topics"]] + others)
            log["steps"].append({"step": "gap_topics", "source": sid, "uncovered": uncovered, **stats})
            data["topics"] += extra
            covered |= {n for t in extra for n in passage_numbers(t["passages"], len(passages))}
        still = [i for i in range(1, len(passages) + 1) if i not in covered]
        if still:
            say(f"      WARNING: still uncovered: {', '.join(passages[i - 1]['section'][:60] for i in still)}")
            log["steps"].append({"step": "coverage_warning", "source": sid, "uncovered": still})

        # Reviewed text wins while the source is unchanged: Gemma's new draft is saved for
        # comparison instead of overwriting human corrections. A changed source is regenerated.
        keep_reviewed = bool(prev) and prev["sha256"] == sha
        if keep_reviewed:
            drafts = {"source": sid, "overview": data["overview"], "topics": data["topics"]}
            draft_path = config.DATA / "drafts" / f"{sid}-{datetime.now():%Y%m%d-%H%M%S}.json"
            _save(draft_path, drafts)
            say(f"      source unchanged: reviewed pages kept; Gemma draft saved to {draft_path.relative_to(config.ROOT)}")
            for t in prev["topics"]:
                say(f"      topic: {t} (updated in place, no duplicate)")
            prev["ingested_at"] = datetime.now().isoformat(timespec="seconds")
            continue

        # drop this source's old contributions, then add the new ones
        for t in list(pages):
            pages[t]["sources"].pop(sid, None)
            if not pages[t]["sources"]:
                del pages[t]
        titles = []
        for topic in data["topics"]:
            title = clean_title(topic["title"], list(pages) + required)
            if required and title not in required:
                # Re-ingest must not invent new names: map to the closest recorded title.
                words = set(title.lower().split())
                title = max(required, key=lambda r: len(words & set(r.lower().split())))
            if title in titles:
                continue
            idx = passage_numbers(topic["passages"], len(passages))
            sections = sorted({passages[i - 1]["section"] for i in idx}) or ["(whole note)"]
            page = pages.setdefault(title, {"sources": {}, "related": []})
            page["sources"][sid] = {"summary": topic["summary"].strip(),
                                    "key_points": [k.strip() for k in topic["key_points"] if k.strip()],
                                    "sections": sections}
            page["generated_at"] = datetime.now().isoformat(timespec="seconds")
            page["reviewed"] = False
            titles.append(title)
            say(f"      topic: {title}")

        manifest[sid] = {
            "raw_path": f.relative_to(config.ROOT / "vault").as_posix(),
            "raw_title": f.stem,
            "original_file": ORIGINAL_FILES.get(f.stem, f.name),
            "sha256": sha,
            "chapter": chapter_title(f),
            "overview": data["overview"].strip(),
            "topics": titles,
            "ingested_at": datetime.now().isoformat(timespec="seconds"),
        }
        changed = True

    if changed and any(not p.get("reviewed") for p in pages.values()):
        say(f"  > linking {len(pages)} topic notes (Gemma picks related notes)")
        summaries = {t: next(iter(p["sources"].values()))["summary"] for t, p in pages.items()}
        for t in pages:
            if pages[t].get("reviewed"):
                continue  # curated links on reviewed pages are kept
            cands = [(o, first_sentence(s)) for o, s in summaries.items() if o != t]
            related, stats = gemma_links(t, summaries[t], cands)
            log["steps"].append({"step": "links", "page": t, **stats})
            seen, keep = set(), []
            for r in related:
                target = clean_title(r["title"], list(pages))
                if target in pages and target != t and target not in seen:
                    seen.add(target)
                    keep.append({"title": target, "why": r["why"].strip()})
            pages[t]["related"] = keep[:3]

    _save(config.MANIFEST, manifest)
    _save(config.PAGES, pages)
    write_wiki(manifest, pages)
    index = retrieval.build_index()

    log["total_seconds"] = round(time.time() - t0, 1)
    log["pages"] = len(pages) + len(manifest)
    log["passages_indexed"] = len(index["passages"])
    log["memory_after"] = llm.memory_snapshot()
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = config.LOG_DIR / f"ingest-{datetime.now():%Y%m%d-%H%M%S}.json"
    _save(log_path, log)
    say(f"  done in {log['total_seconds']}s: {len(pages)} topic notes, {len(manifest)} chapter pages, "
        f"{log['passages_indexed']} passages indexed")
    say(f"  log: {log_path.relative_to(config.ROOT)}")
    return log
