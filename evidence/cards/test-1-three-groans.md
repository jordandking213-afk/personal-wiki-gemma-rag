# Test 1: Direct question, one source

| | |
|---|---|
| **Question** | What are the three groans in Romans 8:18-30? |
| **Mode / execution** | ask · local, offline (Wi-Fi off, see [terminal log](../offline-run/terminal-log.txt)) |
| **Model** | `gemma4:e2b-it-qat` (Gemma 4 E2B, Q4_0) via Ollama 0.34.3, `num_ctx` 8192, temperature 0.1 |
| **Run record** | [ask/20260926-140419…md](../ask/20260926-140419-what-are-the-three-groans-in.md) · [json](../ask/20260926-140419-what-are-the-three-groans-in.json) |
| **Response time / memory** | 6.47 s · model process 4.78 GB |

## Expected (written before building retrieval, [tests/questions.md](../../tests/questions.md))
`vault/raw/Romans 8 Study Notes.md` → "Three groans are mentioned": Creation groans (18-22),
Believers groan (23-25), Holy Spirit groans (23-30).

## Retrieved passages
| | Passage | Section | BM25 |
|---|---|---|---|
| S1 | Romans 8 Study Notes#5 | Holy Spirit groans (23-30) > The Spirit groans, but also prays on our behalf | 7.773 |
| S2 | Romans 8 Study Notes#4 | Holy Spirit groans (23-30) > Jesus groaned when He saw what sin did… | 7.100 |
| S3 | Romans 8 Study Notes#2 | Three groans are mentioned > **Creation groans (18-22)** | 6.521 |
| S4 | Romans 8 Study Notes#6 | Holy Spirit groans (23-30) > God is always at work (verse 28)… | 5.538 |
| S5 | Romans 8 Study Notes#3 | Three groans are mentioned > **Believers groan (23-25)** | 5.532 |

Retrieval: **correct.** All three groans are present. The believers passage ranks 5th, which
is why `TOP_K` was raised from 4 to 5 before this run ([retrieval-tuning.md](../retrieval-tuning.md)).

## Gemma's answer (verbatim)
> The three groans mentioned in Romans 8:18-30 are:
>
> 1. Creation groans (verses 18-22) [S3].
> 2. Holy Spirit groans (verses 23-30) [S1, S4].
> 3. Believers groan (verses 23-25) [S5].

## Citation check
Harness: `OK — cites S1, S3, S4, S5, all provided`. Manual check against the passages:

| Claim | Cited | Supported? |
|---|---|---|
| Creation groans (18-22) | S3 | ✅ The passage heading is exactly "Creation groans (18-22)". |
| Holy Spirit groans (23-30) | S1 | ✅ The heading is "Holy Spirit groans (23-30)", and the text says "The Spirit groans". |
| Holy Spirit groans (23-30) | S4 | ⚠️ Only the section heading supports this. The passage text is about God's plan (v. 28-29). It's a weak citation, not a wrong one. |
| Believers groan (23-25) | S5 | ✅ The heading is exactly "Believers groan (23-25)". |

## Assessment: **PASS**
All three groans are listed with the correct verse ranges, and each has a supporting citation.
Minor issues: the answer lists the groans in a different order than the notes, and [S4] is a
weak supporting citation.
