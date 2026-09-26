# Retrieval tuning (before the offline test runs)

Checked retrieval alone (no model) for the four planned ask questions, as the assignment asks
("inspect retrieval first").

**Finding:** with `TOP_K = 4`, test 1 ("What are the three groans in Romans 8:18-30?") did not
retrieve the *Believers groan (23-25)* passage. BM25 ranking for that question:

| Rank | Passage | BM25 | Words |
|---|---|---|---|
| 1 | Romans 8 Study Notes#5 — Holy Spirit groans > The Spirit groans, but also prays… | 7.773 | 47 |
| 2 | Romans 8 Study Notes#4 — Holy Spirit groans > Jesus groaned… | 7.100 | 15 |
| 3 | Romans 8 Study Notes#2 — Creation groans (18-22) | 6.521 | 94 |
| 4 | Romans 8 Study Notes#6 — Holy Spirit groans > God is always at work… | 5.538 | 88 |
| 5 | **Romans 8 Study Notes#3 — Believers groan (23-25)** | 5.532 | 117 |

The believers passage lost 4th place by 0.006 because BM25 penalizes its length (117 words, the
longest passage). With only 4 passages, Gemma could not have cited all three groans from
their own passages.

**Change:** `TOP_K` raised from 4 to 5 (≈700 words of context, well inside the 8,192-token window).

**Chat retrieval rule, also changed:** a raw BM25 threshold of 2.5 was unreliable on this tiny
corpus: "what's a good dinner recipe" scored 2.83 (matched "return *good* for evil") and would
have triggered a lookup, while "tell me about suffering" scored 1.82 and would not. Replaced with:
look up notes if the message names the study (Romans, a verse like 8:28, "notes"), or if ≥ 50%
of its content words appear in the notes and the top BM25 score is ≥ 1.5.
