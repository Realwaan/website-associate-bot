# 11-crag-relevance-gatekeeper.md

**[CRITICAL]**

## Problem
Standard RAG systems hallucinate answers when asked out-of-domain questions (e.g., asking about company stock options on an IT hardware spec). In enterprise audits, answering unverified queries with confident hallucinations is a fatal flaw. The system must know when to refuse to answer, while also avoiding false refusals caused by paragraph boundary cuts.

## Potentially Related Files
- `app/evaluator.py` - Corrective RAG (CRAG) score threshold evaluator and whole-page promotion badge
- `app/retriever.py` - Hybrid retriever with Tier-2 whole-page escalation scanner
- `app/main.py` - 2-tier defense refusal flow and status response
- `tests/test_pipeline.py` - evaluator acceptance, whole-page promotion, and refusal tests

## What to Fix
1. Inspect the top dense similarity score of the retrieved chunks against `SIMILARITY_THRESHOLD = 0.50`.
2. If chunk similarity is below threshold (< 0.50), escalate up the Document AST to Tier-2 Whole-Page Scanning to recover multi-paragraph continuity across candidate pages.
3. If Whole-Page Scanning verifies grounding (>= 0.50), promote context to `SYNTHESIZE` with audit badge: `🛡️ GROUNDED • PROMOTED TO PAGE SCAN ({confidence}%)`.
4. If relevance remains below threshold (< 0.50) even after Whole-Page Scanning, trigger a `REFUSE` status with an audit badge: `⚠️ OUT-OF-BOUNDS (0% Match)`.
5. Generate an explicit defense refusal message stating the document does not contain verified data for the query.
6. Provide a baseline comparison so judges can see Plain Gemma hallucinating while AuditGuard correctly refuses.

## Acceptance Criteria
- Out-of-bounds queries ("What is the secret recipe for Coca-Cola?") trigger refusal even after whole-page escalation.
- Borderline queries split across paragraphs promote cleanly to whole-page synthesis with clear grounding percentage.
- In-bounds queries proceed to Gemma 4 synthesis with clear grounding percentage.
- Confidence scores are formatted correctly without multiplier bugs.
- Unit tests verify `REFUSE`, `PROMOTED TO PAGE SCAN`, and `SYNTHESIZE` execution paths.
