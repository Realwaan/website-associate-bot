# 12-formal-nli-entailment-evaluator.md

**[PRIORITY]**

## Problem
Cosine similarity thresholding ($	au = 0.50$) only measures lexical/vector proximity; it cannot determine whether a retrieved excerpt logically entails, is neutral to, or contradicts a user query hypothesis. Competing enterprise guardrails leverage Natural Language Inference (NLI) to provide mathematical proof of contextual grounding.

## Potentially Related Files
- `app/evaluator.py` - CRAG relevance gatekeeper with NLI scoring
- `app/discrepancy_scanner.py` - contradiction hunter integration
- `tests/test_pipeline.py` - evaluator entailment verification tests

## What to Fix
1. Enhance `evaluate_relevance()` in `app/evaluator.py` to evaluate semantic entailment alongside dense similarity.
2. Formulate explicit entailment classifications: `ENTAILED` (grounded, synthesize), `NEUTRAL` (insufficient evidence, refuse), or `CONTRADICTORY` (evidence directly refutes query premise).
3. Compute an NLI confidence score combining vector similarity and logical premise alignment.
4. Update response badges with explicit grounding proof (e.g., `🛡️ ENTAILED GROUNDING (92.4%)` vs `⚠️ OUT-OF-BOUNDS`).
5. Ensure zero external cloud API dependencies; operate with deterministic sub-millisecond local heuristics and local embeddings.

## Acceptance Criteria
- Grounded query-context pairs receive `ENTAILED` status with `SYNTHESIZE` directive.
- Queries seeking facts missing from context trigger `NEUTRAL` status with `REFUSE` defense.
- Evaluator completes execution in $< 5	ext{ ms}$ on local CPU.
- Unit tests verify both entailment and refusal logic paths.\n