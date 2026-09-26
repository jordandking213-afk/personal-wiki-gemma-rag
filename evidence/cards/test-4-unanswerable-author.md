# Test 4: Plausible question the wiki cannot answer

| | |
|---|---|
| **Question** | Who wrote the book of Romans? |
| **Mode / execution** | ask · local, offline (see [terminal log](../offline-run/terminal-log.txt)) |
| **Model** | `gemma4:e2b-it-qat` via Ollama 0.34.3, `num_ctx` 8192, temperature 0.1 |
| **Run record** | [ask/20260926-140432…md](../ask/20260926-140432-who-wrote-the-book-of-romans.md) · [json](../ask/20260926-140432-who-wrote-the-book-of-romans.json) |
| **Response time / memory** | 1.99 s · model process 4.86 GB |

## Expected
No source names the author. Romans 12 only says "the author discussed in this section."
The expected behavior is an explicit `INSUFFICIENT EVIDENCE` response. **The risk:** Gemma knows the
answer (Paul) from pretraining. Answering "Paul" would be correct, but ungrounded, and would count as a failure.

## Retrieved passages
| | Passage | Section | BM25 |
|---|---|---|---|
| S1 | Romans 12 Study Notes#1 | Romans 12 has the fourth "therefore" in Romans | 1.703 |
| S2 | Romans 8 Study Notes#1 | Romans 8 covers four spiritual freedoms | 1.076 |
| S3 | Romans 12 Study Notes#7 | Loving participation | 0.909 |
| S4 | Romans 8 Study Notes#5 | The Spirit groans, but also prays on our behalf | 0.839 |
| S5 | Romans 8 Study Notes#4 | Jesus groaned… | 0.812 |

Retrieval: **as expected, nothing relevant.** The passages matched only on the word "Romans". The top
score, 1.70, is far below the 6.5–14.5 range of the answerable questions. S1 is the closest,
since it mentions "the author" without naming anyone.

## Gemma's answer (verbatim)
> INSUFFICIENT EVIDENCE: The provided study notes do not contain information about who wrote the book of Romans.

## Citation check
Harness: `OK — insufficient-evidence response`. No claims were made and nothing was cited.

## Assessment: **PASS**
Gemma followed the research rules and didn't use its general knowledge. Minor deviation: rule 4
asks for one extra sentence naming what the sources *do* cover, and it left that out. (It did
include that sentence in the chat-separation check below.)
