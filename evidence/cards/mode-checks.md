# Chat and search mode checks

All checks ran offline in the same session as the ask tests (14:02–14:06, see the
[terminal log](../offline-run/terminal-log.txt)). Model: `gemma4:e2b-it-qat` via Ollama 0.34.3.
Full chat transcript, including the notes each turn retrieved:
[chat/20260926-140432-chat-session.md](../chat/20260926-140432-chat-session.md).

| # | Check | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| 1 | Casual chat | `what can we do?` | Capabilities, no lookup, no refusal | `[no notes lookup]`. Listed discussing ideas, brainstorming questions/devotionals/outlines, and summaries | ✅ PASS |
| 2 | Casual chat | `what can you help me with?` | Same | `[no notes lookup]`. Listed discussion, study plans, summaries, looking things up. No citations, no "insufficient evidence" | ✅ PASS |
| 3 | Draft with notes | `Give me a short 3-step plan for a small group discussion on Romans 12` | Looks up notes, cites note-based claims, plan labeled as a suggestion | `[looked up notes (message refers to the study)]`. 3-step plan citing S1, S2, S3, S5 (all Romans 12). Offered as "a short, three-step plan you could use" | ⚠️ PASS with issues (below) |
| 4 | Follow-up | `make that shorter` | Uses conversation, no new lookup | `[no notes lookup]`. Condensed the same three steps (Foundation / Dedication / Love) into three one-line questions | ✅ PASS |
| 5 | Claim made only in chat | `Just so you know, our study group meets on Tuesdays` | Acknowledged conversationally | Acknowledged ("Knowing that you meet on Tuesdays…"), **but a notes lookup was triggered and a citation was wrong** (below) | ❌ FAIL (retrieval + citation) |
| 6 | Search | `./wiki search "living sacrifice"` | Original passages + paths, no generated answer, no model | 3 passages from `vault/raw/Romans 12 Study Notes.md` (body/will/mind as sacrifice) with BM25 scores. Header shows `model: none (retrieval only)`. [Record](../search/20260926-140412-living-sacrifice.md) | ✅ PASS |
| 7 | Chat ≠ evidence | `./wiki ask "When does the study group meet?"` (after check 5) | INSUFFICIENT EVIDENCE: chat history is not a source | `INSUFFICIENT EVIDENCE: The study notes do not contain this information. The study notes discuss Romans 8:18-30…` [Record](../ask/20260926-140620-when-does-the-study-group-meet.md) | ✅ PASS |

## Issues found

**Check 3 (minor).** Two citations overstate their passage:
- "Present your bodies as a living sacrifice" [S1]: this is scripture wording from Gemma's own
  knowledge. S1 says "Your body is a living sacrifice to give to God." The meaning is the same, but the quoted text isn't in the source.
- "Romans 12:1 is the 'therefore' of everything else" [S2]: the notes say it is the "therefore" of
  *dedication* and "the basis for the other relationships" in this section. "Everything else" overstates that.

**Check 5 (real failure, two causes).**
1. *False-positive retrieval:* the word "study" in "study group" matched the chat rule that
   triggers a lookup for study words (`CHAT_STUDY_WORDS` in `wiki_cli/config.py`), so the harness
   retrieved three Romans 8 passages for a scheduling remark.
2. *Wrong citation that passed the check:* Gemma wrote "present our bodies as a living
   sacrifice? [S1]", but S1 on this turn was the Romans 8 passage about the Spirit praying on our behalf.
   The harness citation check reported `OK` because it only verifies that the cited number
   exists, not that the passage supports the claim. The citation numbers had also changed
   between turns: in check 3, S1 *was* the living-sacrifice passage, so Gemma likely reused a
   number from earlier in the conversation.

The important boundary still held: the Tuesday claim did not leak into ask mode (check 7).
