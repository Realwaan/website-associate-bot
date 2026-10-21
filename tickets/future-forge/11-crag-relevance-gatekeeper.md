# 2-Tier CRAG Relevance Gatekeeper with Whole-Page Escalation

**[CRITICAL]**

## Problem
Standard RAG systems hallucinate answers when asked out-of-domain questions (e.g., asking about company stock options on an IT hardware spec). In enterprise audits, answering unverified queries with confident hallucinations is a fatal flaw. The system must know when to refuse to answer, while also avoiding false refusals caused by paragraph boundary cuts or fabricating artificial lexical boosts.

## Potentially Related Files
- `app/evaluator.py` - Corrective RAG (CRAG) score threshold evaluator and whole-page promotion badge
- `app/retriever.py` - hybrid retriever with Tier-2 whole-page escalation scanner
- `app/main.py` - 2-tier defense refusal flow and status response
- `tests/test_pipeline.py` - evaluator acceptance, whole-page promotion, and refusal tests

## What to Fix
1. Inspect the top dense similarity score of retrieved chunks against `SIMILARITY_THRESHOLD = 0.50`.
2. If chunk similarity is below threshold (< 0.50), escalate up the Document AST to Tier-2 Whole-Page Scanning to recover multi-paragraph continuity across candidate pages.
3. In `escalate_page_scan`, use exact word-boundary token matching without artificial lexical score inflation (no forcing scores >= 0.725 or hardcoding dense=1.0).
4. If Whole-Page Scanning verifies grounding (>= 0.50), promote context to `SYNTHESIZE` with audit badge: `🛡️ GROUNDED • PROMOTED TO PAGE SCAN ({confidence}%)`.
5. If relevance remains below threshold (< 0.50) even after Whole-Page Scanning, trigger a `REFUSE` status with an audit badge: `⚠️ OUT-OF-BOUNDS (0% Match)`.
6. Generate an explicit defense refusal message stating the document does not contain verified data for the query.

## Acceptance Criteria
- Out-of-bounds queries trigger clean refusal with `status: REFUSE` and 0% match badge.
- Borderline queries split across paragraphs promote cleanly to whole-page synthesis with true measured grounding percentage.
- In-bounds queries proceed to Gemma 4 synthesis with measured grounding score.
- Unit tests verify `REFUSE`, `PROMOTED TO PAGE SCAN`, and `SYNTHESIZE` execution paths.
