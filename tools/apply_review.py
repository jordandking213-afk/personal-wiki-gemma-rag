"""Human review pass over Gemma's generated wiki pages (run once after ingest).

Every correction below was made by comparing a generated page against the original note in
vault/raw/. The raw evidence is never edited; only the generated wiki content changes.
Writes evidence/ingest/review-log.md with the before/after text of each change.

Usage: python3 tools/apply_review.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wiki_cli import config, retrieval  # noqa: E402
from wiki_cli.ingest import write_wiki  # noqa: E402

R8, R10, R12 = "romans-08-study-notes", "romans-10-study-notes", "romans-12-study-notes"

# old title -> new title (Gemma's name did not match the note's subject)
RENAMES = {
    "Foundation of Dedication": "Four Therefores in Romans",   # page is about the four "therefores"
    "Living Sacrifice": "Body as Living Sacrifice",             # parallels Mind/Will as Sacrifice
    "Relationship to Others": "Relationships with Believers",   # notes: "Relationship (to other believers)"
    "Suffering and Groans": "Three Groans of Suffering",        # the notes' own structure
    "God's Sovereignty": "God's Perfect Plan",                  # the notes say "perfect plan"
}

# pages that cover the same passage and are merged into one note
MERGES = {"Relationship to Enemies": ["Love in Dealing with Enemies", "Viewing Revenge and Justice"]}

# corrected content: (page, source) -> fields, each with the reason for the change
CORRECTIONS = {
    ("Reasons for Rejection", R10): {
        "why": "Gemma wrote that Israel 'was rejected'; the notes describe Israel rejecting God's way of salvation.",
        "summary": "Israel rejected God's way of salvation because they did not feel a need for it, made and worshipped their own traditions, were proud and self-righteous, and misunderstood their own law (Romans 10:1-13).",
        "key_points": [
            "Did not feel a need for salvation; thought they were fine and could save themselves.",
            "Zealous for God, but made their own traditions and worshipped them.",
            "Proud and self-righteous; refused to listen and learn.",
            "Misunderstood their own law: the law was a signpost that could not take them to the destination; it only leads the sinner to the savior.",
            "The law cannot only be outwardly obeyed; it has to be obeyed in the heart as well.",
            "Open question from the study: is there a difference between obeying the Lord and calling on the Lord?",
        ],
    },
    ("Remedy for Rejection", R10): {
        "why": "Gemma said the remedy 'involves a missionary program' and turned an open question into a claim.",
        "summary": "Romans 10:14-17 gives the remedy for Israel's rejection: to believe, one must first hear. The notes point out that this passage is used for missionary programs.",
        "key_points": [
            "To believe, one must first hear.",
            "This passage is used for missionary programs.",
            "Open question from the study: are believing and obeying interchangeable?",
        ],
    },
    ("Results of Rejection", R10): {
        "why": "Accurate; added verse range.",
        "summary": "Romans 10:18-21 describes the results: Israel is guilty because they did hear, the message is shared with the Gentiles because of Israel's rejection, and God still yearns for His people.",
    },
    ("Four Therefores in Romans", R12): {
        "why": "Gemma framed this as 'foundation of dedication'; the passage lists all four 'therefores'. Added missing details.",
        "summary": "Romans 12:1 is the fourth \"therefore\" in Romans. The notes list all four as turning points in the letter, with the \"therefore\" of dedication as the basis for the relationships discussed in Romans 12.",
        "key_points": [
            "Romans 3:20 is the \"therefore\" of condemnation: the whole world is guilty before God.",
            "Romans 5:1 is the \"therefore\" of justification.",
            "Romans 8:1 is the \"therefore\" of assurance.",
            "Romans 12:1 is the \"therefore\" of dedication, the basis for the other relationships discussed in this section.",
        ],
    },
    ("Body as Living Sacrifice", R12): {
        "why": "Gemma wrote 'Isaac died in obedience'; the notes say a ram took his place.",
        "summary": "The first step of dedication is giving your body to God as a living sacrifice. The notes name two living sacrifices in the Bible: Isaac and Jesus Christ.",
        "key_points": [
            "Your body is a living sacrifice to give to God.",
            "Isaac (Genesis 22) would have died in obedience to God, but a ram took his place. It still counts: he died to self and willingly yielded to God's will.",
            "Jesus Christ (the Gospels) actually died in sacrifice.",
        ],
    },
    ("Mind as Sacrifice", R12): {
        "why": "Accurate; restored the 'conformer' contrast and the role of meditating on God's Word.",
        "key_points": [
            "The world wants to change your mind with external pressure; the Holy Spirit changes your mind by releasing power within.",
            "If the world is in control, you are a conformer; if God controls your thinking, you are a transformer.",
            "Spending time meditating on and memorizing God's Word is part of how God makes you more spiritual.",
        ],
    },
    ("Will as Sacrifice", R12): {
        "why": "Accurate; restored that 'willpower' often fails and the 'won't power' idea.",
        "key_points": [
            "Your mind controls your body, and your will controls your mind.",
            "\"Willpower\" often fails; yielding our will to God lets His power take over and gives us willpower (and \"won't power\").",
            "Surrender happens through disciplined prayer: \"Not my will, but thy will be done.\"",
            "Pray about everything and yield the plans of the day to Him.",
        ],
    },
    ("Relationships with Believers", R12): {
        "why": "Gemma's 'neither under nor over-evaluating is pride' reversed the point; restored 'no gift is greater'.",
        "summary": "Romans 12 describes three parts of relating to other believers: honest evaluation of one's gifts, faithful cooperation, and loving participation.",
        "key_points": [
            "Honest evaluation: each Christian should identify their spiritual gifts and ministries, ideally in a local church.",
            "Do not under- or over-evaluate yourself; both are examples of pride.",
            "Faithful cooperation: work with others even if you don't get along. No one gift is better or greater than others.",
            "Gifts are tools to build with, not toys to play with or weapons to fight with.",
            "Loving participation: attitude matters. Love is the circulatory system of the spiritual body, and it should be honest and humble, not hypocritical or proud.",
            "Romans 12:12: be joyful in hope, patient in affliction, and faithful in prayer. Share the burdens of others.",
        ],
    },
    ("Relationship to Enemies", R12): {
        "why": "Merged two thin notes about one passage. Gemma turned the notes' questions into instructions ('Justice should be viewed as love').",
        "summary": "Romans 12 teaches returning good for the evil we are met with, which requires love. The notes end with open reflection questions about revenge and justice.",
        "key_points": [
            "Returning good in exchange for evil requires love.",
            "Having enemies because we are impatient and lack love is different from having enemies because we follow Christ.",
            "Reflection questions: How do we view revenge? Do we position ourselves as better, or less deserving of \"justice,\" than others? Do we view justice as love?",
        ],
    },
    ("Four Spiritual Freedoms", R8): {
        "why": "Added verse ranges; the notes label 8:31-39 only as 'No Separation'. Noted the commentary used.",
        "summary": "Using Wiersbe's commentary, the notes divide Romans 8 into four spiritual freedoms. The study focuses on the third, freedom from discouragement (8:18-30).",
        "key_points": [
            "8:1-4: Freedom from judgment (no condemnation).",
            "8:5-17: Freedom from defeat (no obligation; because we cannot save ourselves, submit to God).",
            "8:18-30: Freedom from discouragement (no frustration).",
            "8:31-39: No separation.",
        ],
    },
    ("Three Groans of Suffering", R8): {
        "why": "Restored the labor-pain comparison, the fitness example, and the Spirit's intercession (a coverage gap in earlier runs).",
        "summary": "Romans 8:18-30 addresses suffering and how believers are free from discouragement. The notes identify three groans: creation (18-22), believers (23-25), and the Holy Spirit (23-30).",
        "key_points": [
            "Creation groans (18-22): suffering is a result of Adam's sin, but it is not useless. The groans are compared to a woman in labor: pain now, but something beautiful results and the pain ends.",
            "Embrace today's sufferings to build up to tomorrow, like physical fitness: you break down your body to be built back up stronger.",
            "Everyone suffers, but not everyone has the same solution, and not all solutions are equal.",
            "Believers groan (23-25): we have a taste of the glory to come but are anxious to get there.",
            "The Holy Spirit groans (23-30): Jesus groaned when He saw what sin did to mankind (Mark 7:34; John 11:33, 38).",
            "The Spirit also prays on our behalf. We do not know God's will or what to pray for, but the Spirit intercedes to share the burden.",
        ],
    },
    ("Hope and Assurance", R8): {
        "why": "Gemma stated the adoption climax 'at the Rapture'; the notes say it is likened to the Rapture. Added the closing reflection.",
        "key_points": [
            "Adoption = redemption of the body when Jesus comes back.",
            "Adoption begins when we are saved and receive the Holy Spirit (\"the Spirit of adoption\"); its \"climax\" is likened to the Rapture, when we receive glorified bodies.",
            "Example: being saved is like agreeing to an adoption; the climax is when the child actually moves into the home.",
            "Believers still have hope because they know the climax of that adoption is coming.",
            "Closing reflection: faith, hope, and love (1 Corinthians 13:13); faith is the assurance of things hoped for (Hebrews 11:1).",
        ],
    },
    ("God's Perfect Plan", R8): {
        "why": "Gemma presented predestination as settled; the notes mark it '???' for group discussion. Restored the out-of-context warning.",
        "summary": "God is always at work (verse 28) and has a perfect plan (verse 29) for those who love Him and are called according to His purpose.",
        "key_points": [
            "God is always at work (verse 28) and has a perfect plan (verse 29).",
            "This verse is often taken out of context: \"for those who love God\" and \"called according to his purpose\" are critical and sometimes left out.",
            "Open question marked for group discussion: does predestination apply only to saved people?",
            "God does not predestine people to be eternally condemned.",
        ],
    },
}

# curated related links, replacing Gemma's (which leaned on vague hub links)
LINKS = {
    "Reasons for Rejection": [
        ("Remedy for Rejection", "The next verses answer the problem: to believe, one must first hear."),
        ("Results of Rejection", "What followed Israel's rejection, including the message going to the Gentiles."),
        ("Four Therefores in Romans", "Romans 3:20 says the whole world is guilty, the opposite of 'thought they were fine.'"),
    ],
    "Remedy for Rejection": [
        ("Reasons for Rejection", "The problem this remedy addresses."),
        ("Results of Rejection", "What happened after Israel heard but did not believe."),
    ],
    "Results of Rejection": [
        ("Reasons for Rejection", "Why Israel rejected the message in the first place."),
        ("Remedy for Rejection", "Hearing is required to believe, and the notes say Israel did hear."),
    ],
    "Four Therefores in Romans": [
        ("Four Spiritual Freedoms", "Romans 8:1, the 'therefore' of assurance, opens the chapter's four freedoms."),
        ("Body as Living Sacrifice", "Romans 12:1, the 'therefore' of dedication, begins with offering the body."),
        ("Reasons for Rejection", "Romans 3:20's condemnation explains why no one can save themselves."),
    ],
    "Body as Living Sacrifice": [
        ("Mind as Sacrifice", "The second step of dedication."),
        ("Will as Sacrifice", "The third step; the will controls the mind, which controls the body."),
        ("Four Therefores in Romans", "Dedication is the fourth 'therefore' of Romans."),
    ],
    "Mind as Sacrifice": [
        ("Body as Living Sacrifice", "The first step of dedication."),
        ("Will as Sacrifice", "Your will controls your mind, so the next step is yielding the will."),
    ],
    "Will as Sacrifice": [
        ("Mind as Sacrifice", "The mind is what the will controls."),
        ("Three Groans of Suffering", "Where we don't know what to pray for, the Spirit intercedes; both notes center on prayer."),
    ],
    "Relationships with Believers": [
        ("Relationship to Enemies", "The same chapter extends love from fellow believers to enemies."),
        ("Hope and Assurance", "Romans 12:12's 'joyful in hope' draws on the hope described in Romans 8."),
        ("Three Groans of Suffering", "We share each other's burdens as the Spirit shares ours."),
    ],
    "Relationship to Enemies": [
        ("Relationships with Believers", "Love among believers is the foundation for returning good for evil."),
    ],
    "Four Spiritual Freedoms": [
        ("Three Groans of Suffering", "The study's focus: freedom from discouragement in 8:18-30."),
        ("Four Therefores in Romans", "Romans 8:1 is the 'therefore' of assurance."),
    ],
    "Three Groans of Suffering": [
        ("Hope and Assurance", "The believers' groan looks ahead to the climax of adoption."),
        ("God's Perfect Plan", "Verses 28-29 close the passage: God is at work through the suffering."),
        ("Four Spiritual Freedoms", "Where this passage fits in Romans 8."),
    ],
    "Hope and Assurance": [
        ("Three Groans of Suffering", "Hope is what carries believers through the groaning."),
        ("God's Perfect Plan", "The plan in verses 28-29 is the basis for that hope."),
    ],
    "God's Perfect Plan": [
        ("Three Groans of Suffering", "The suffering that this promise speaks into."),
        ("Hope and Assurance", "Why believers can hope while they wait."),
    ],
}

OVERVIEWS = {
    R10: ("Gemma's 'Israel's rejection' was ambiguous and was misread elsewhere as Israel being rejected.",
          "This study of Romans 10 examines why Israel rejected God's way of salvation (verses 1-13), the remedy for that rejection (14-17), and its results (18-21), including the message being shared with the Gentiles."),
    R12: ("Gemma listed 'relationships with God and others'; the notes cover relationships with believers and enemies.",
          "This study of Romans 12 starts from the fourth \"therefore\" in Romans, the \"therefore\" of dedication. It covers three steps of dedication (body, mind, and will as sacrifices to God) and how that shapes relationships with other believers and with enemies."),
    R8: ("Accurate; tightened to match the notes' focus on 8:18-30.",
         "This study of Romans 8:18-30 places the passage within the chapter's four spiritual freedoms and focuses on freedom from discouragement. It covers the three groans (creation, believers, and the Holy Spirit), the hope of adoption, and God's perfect plan for those who love Him."),
}


def main():
    pages = json.loads(config.PAGES.read_text())
    manifest = json.loads(config.MANIFEST.read_text())
    log = ["# Wiki Review Log", "",
           "Each generated page was checked against the original note in `vault/raw/`. Gemma's",
           "unreviewed output is archived in `evidence/ingest/run-3-gemma-before-review/`.", ""]

    log.append("## Renames")
    for old, new in RENAMES.items():
        pages[new] = pages.pop(old)
        for m in manifest.values():
            m["topics"] = [new if t == old else t for t in m["topics"]]
        log.append(f"- `{old}` → `{new}`")

    log += ["", "## Merges"]
    for new, olds in MERGES.items():
        merged = {"sources": {}, "related": [], "generated_at": pages[olds[0]]["generated_at"]}
        for old in olds:
            for sid, c in pages.pop(old)["sources"].items():
                prev = merged["sources"].setdefault(sid, {"summary": "", "key_points": [], "sections": []})
                prev["sections"] = sorted(set(prev["sections"]) | set(c["sections"]))
        pages[new] = merged
        for m in manifest.values():
            topics = []
            for t in m["topics"]:
                t = new if t in olds else t
                if t not in topics:
                    topics.append(t)
            m["topics"] = topics
        log.append(f"- {', '.join(f'`{o}`' for o in olds)} → `{new}`")

    log += ["", "## Content corrections"]
    for (title, sid), fix in CORRECTIONS.items():
        c = pages[title]["sources"][sid]
        log += ["", f"### {title}", f"Reason: {fix['why']}", ""]
        for field in ("summary", "key_points"):
            if field in fix:
                before = c.get(field) or "(none)"
                log += [f"- **{field} before:** {json.dumps(before, ensure_ascii=False)}",
                        f"- **{field} after:** {json.dumps(fix[field], ensure_ascii=False)}"]
                c[field] = fix[field]

    log += ["", "## Chapter overviews"]
    for sid, (why, text) in OVERVIEWS.items():
        log += [f"- **{manifest[sid]['chapter']}**: {why}", f"    - before: {manifest[sid]['overview']}",
                f"    - after: {text}"]
        manifest[sid]["overview"] = text
        manifest[sid]["reviewed"] = True

    log += ["", "## Related links",
            "Gemma's links leaned on vague hub connections (most notes linked to the same plan/sovereignty note",
            "with generic reasons). Replaced with curated links whose reasons come from the notes."]
    for title, links in LINKS.items():
        assert title in pages, title
        for target, _ in links:
            assert target in pages, target
        pages[title]["related"] = [{"title": t, "why": w} for t, w in links]
    for p in pages.values():
        p["reviewed"] = True

    config.PAGES.write_text(json.dumps(pages, indent=2, ensure_ascii=False))
    config.MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    write_wiki(manifest, pages)
    retrieval.build_index()
    out = config.EVIDENCE / "ingest" / "review-log.md"
    out.write_text("\n".join(log) + "\n")
    print(f"reviewed {len(pages)} topic notes; log: {out.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
