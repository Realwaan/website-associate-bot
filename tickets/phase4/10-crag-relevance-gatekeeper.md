# 10-crag-relevance-gatekeeper.md

**[CRITICAL]**

## Problem
Standard RAG systems hallucinate answers when asked out-of-domain questions (e.g., asking about company stock options on an IT hardware spec). In enterprise audits, answering unverified queries with confident hallucinations is a fatal flaw. The system must know when to refuse to answer.

## Potentially Related Files
- `app/evaluator.py` - Corrective RAG (CRAG) score threshold evaluator
- `app/main.py` - defense refusal flow and status response
- `tests/test_pipeline.py` - evaluator acceptance and refusal tests

## What to Fix
1. Inspect the top dense similarity score of the retrieved chunks against `SIMILARITY_THRESHOLD = 0.50`.
2. If similarity is below the threshold or chunks are empty, trigger a `REFUSE` status with an audit badge: `⚠️ OUT-OF-BOUNDS (0% Match)`.
3. Generate an explicit defense refusal message stating the document does not contain verified data for the query.
4. When grounded, return `SYNTHESIZE` status with confidence percentage and `🛡️ GROUNDED` badge.
5. Provide a baseline comparison so judges can see Plain Gemma hallucinating while AuditGuard correctly refuses.

## Acceptance Criteria
- Out-of-bounds queries ("What is the secret recipe for Coca-Cola?") trigger immediate refusal.
- In-bounds queries proceed to Gemma 4 synthesis with clear grounding percentage.
- Confidence scores are formatted correctly without multiplier bugs.
- Unit tests verify both `REFUSE` and `SYNTHESIZE` execution paths.
