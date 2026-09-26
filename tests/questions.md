# Ask-Mode Test Set (written before building retrieval)

Kept outside `vault/` so the harness can never retrieve this answer key.
Wiki purpose: "This serves as a guide that unpacks sections from Romans 8, 10, and 12 from the Bible."

| # | Type | Question | Expected source | Expected passage / behavior |
|---|------|----------|-----------------|------------------------------|
| 1 | Direct, one source | What are the three groans in Romans 8:18-30? | `vault/raw/Romans 8 Study Notes.md` | "Three groans are mentioned" → Creation groans (18-22), Believers groan (23-25), Holy Spirit groans (23-30) |
| 2 | Worded differently from source | Why couldn't the Jewish law bring Israel to salvation? | `vault/raw/Romans 10 Study Notes.md` | "Misunderstood their own law" → "Law was a signpost, but could not take them to their destination…it only leads the sinner to the savior"; "has to be obeyed in the heart as well" |
| 3 | Connects two sources | How does Romans 8:1 fit into the "therefore" passages in Romans, and what does Romans 8 say that freedom looks like? | `vault/raw/Romans 12 Study Notes.md` + `vault/raw/Romans 8 Study Notes.md` | Romans 12: "Romans 8:1 is the 'therefore' of assurance" (one of four: 3:20 condemnation, 5:1 justification, 8:1 assurance, 12:1 dedication). Romans 8: four spiritual freedoms — judgment, defeat, discouragement, (no) separation |
| 4 | Unanswerable | Who wrote the book of Romans? | none | Notes never name the author (Romans 12 only says "the author"). Expected: `INSUFFICIENT EVIDENCE`. Risk: Gemma knows "Paul" from pretraining and may answer from general knowledge — that would be a failure. |

## Mode-boundary checks
- Chat: "what can we do?" and "what can you help me with?" → capability explanation, no notes lookup, no citations, no refusal.
- Chat follow-up: ask for a short plan/draft, then "make that shorter" → uses conversation.
- Search: `wiki search "living sacrifice"` → original passages + paths, no generated answer.
- Chat-vs-ask separation: state a claim only in chat (e.g. "the study group meets on Tuesdays"), then `wiki ask "When does the study group meet?"` → must be INSUFFICIENT EVIDENCE.
