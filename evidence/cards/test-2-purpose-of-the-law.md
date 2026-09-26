# Test 2: Answerable question, worded differently from the source

| | |
|---|---|
| **Question** | Why couldn't the Jewish law bring Israel to salvation? |
| **Mode / execution** | ask · local, offline (see [terminal log](../offline-run/terminal-log.txt)) |
| **Model** | `gemma4:e2b-it-qat` via Ollama 0.34.3, `num_ctx` 8192, temperature 0.1 |
| **Run record** | [ask/20260926-140423…md](../ask/20260926-140423-why-couldn-t-the-jewish-law.md) · [json](../ask/20260926-140423-why-couldn-t-the-jewish-law.json) |
| **Response time / memory** | 3.69 s · model process 4.80 GB |

## Expected
`vault/raw/Romans 10 Study Notes.md` → "Misunderstood their own law" → "Law was a signpost, but
could not take them to their destination…it only leads the sinner to the savior"; "has to be
obeyed in the heart as well."

**Wording difference being tested:** the question says "Jewish law" and "bring … to salvation."
The notes never say "Jewish" and describe the law as a "signpost" to a "destination."

## Retrieved passages
| | Passage | Section | BM25 |
|---|---|---|---|
| S1 | Romans 10 Study Notes#1 | **Israel rejections — Reasons for their rejection 1-13** | 9.052 |
| S2 | Romans 10 Study Notes#3 | Results of their rejection 18-21 | 3.850 |

Retrieval: **correct.** The expected passage ranks first, matched on "law", "Israel" and "salvation"
("Did not feel need for salvation"). Only 2 passages scored above zero.

## Gemma's answer (verbatim)
> The Jewish law could not bring Israel to salvation because it was misunderstood. The notes
> state that the law "was a signpost, but could not take them to their destination…it only
> leads the sinner to the savior" [S1]. Furthermore, the law cannot only be outwardly obeyed;
> it must also be obeyed in the heart [S1].

## Citation check
Harness: `OK — cites S1, all provided`. Manual check:

| Claim | Cited | Supported? |
|---|---|---|
| Israel misunderstood the law | S1 | ✅ "Misunderstood their own law" |
| Signpost quote | S1 | ✅ Quoted exactly from the passage |
| Must be obeyed in the heart, not only outwardly | S1 | ✅ "The law cannot only be outwardly obeyed, has to be obeyed in the heart as well" |

## Assessment: **PASS**
The answer is grounded, and the quote is accurate even though the question used different wording.
