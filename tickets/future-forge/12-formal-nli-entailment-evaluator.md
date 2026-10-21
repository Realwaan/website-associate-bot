# CRAG Composite Grounding and Epistemic Humility Evaluator

**[PRIORITY]**

## Problem
Cosine similarity thresholding alone only measures topical proximity; it cannot determine whether an excerpt contains the specific factual keywords necessary to answer a query. Conversely, claiming a 'Formal NLI Entailment' cross-encoder when none is loaded (or faking scores with arbitrary multipliers like `1.08`) is mathematically false and dangerous in enterprise legal audits.

## Potentially Related Files
- `app/evaluator.py` - CRAG composite grounding score evaluator
- `app/generator.py` - answer synthesis with grounding badges
- `tests/test_pipeline.py` - evaluator grounding and refusal verification tests

## What to Fix
1. Refactor `evaluate_relevance(retrieved_chunks, query)` in `app/evaluator.py` to compute a mathematically sound composite grounding score:
   `Grounding Score = 0.60 * Dense Cosine Similarity + 0.40 * Lexical Keyword Recall`.
2. Parse query terms into informative keywords using regex word-boundary matching (`\b[a-zA-Z0-9_\-\.]+\b`) and a comprehensive stopword filter.
3. Measure lexical recall as the fraction of query keywords actively present in retrieved passage text.
4. If composite score >= 0.50, assign `status = 'SYNTHESIZE'` with badge `🛡️ VERIFIED GROUNDING ({grounding_pct}%)`.
5. If composite score < 0.50, assign `status = 'REFUSE'` with badge `⚠️ OUT-OF-BOUNDS (0% Match)` and defense refusal directive.
6. Eliminate all fake `* 1.08` multipliers and unread query parameter stubs.

## Acceptance Criteria
- Grounded query-context pairs receive `SYNTHESIZE` status with true composite grounding percentage.
- Queries seeking missing facts trigger `REFUSE` status with epistemic humility.
- Evaluator completes execution in < 5 ms on local CPU without external API calls.
- Unit tests verify composite grounding calculation, keyword parsing, and refusal thresholds.
