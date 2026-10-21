# Cross-Modal Contradiction Hunter for Prose and Visual Evidence

**[CRITICAL]**

## Problem
A major source of corporate fraud and compliance failure is discrepancies between prose claims and embedded charts (e.g., text claims '99.9% uptime guarantee', but the linked table shows a 98.2% breach). Using crude substring matches like 'up' and '-' causes catastrophic false positives (flagging words like 'uptime', 'support', or standard table hyphens). Bypassing LLM vision validation also prevents verifying real chart contents.

## Potentially Related Files
- `app/discrepancy_scanner.py` - regex boundary scanner and multimodal verification
- `app/main.py` - document contradiction audit endpoint `/api/discrepancies`
- `tests/test_discrepancy_scanner.py` - discrepancy rules and end-to-end scanner tests

## What to Fix
1. Implement word-boundary keyword matching for growth and decline terms, eliminating naive substrings ('up', '-') that trigger on 'uptime' or table punctuation.
2. Establish domain-calibrated percentage discrepancy tolerances: strict 0.5% tolerance for SLA/uptime metrics and 2.0% for general financial/business metrics.
3. Implement deep multimodal verification using Google GenAI / Gemma vision to inspect extracted WebP crops and compare actual visual evidence against author prose.
4. Ensure graceful heuristic fallback if vision API is unreachable, clearly indicating the audit method used.
5. Return structured consistency report with finding types (`ALIGN`, `CAUTION`, `CONTRADICTION`), excerpt citations, and document consistency scores.

## Acceptance Criteria
- Genuine contradictions (e.g., text 99.9% vs table 98.2%) are flagged with `CONTRADICTION`.
- Standard operational words ('uptime', 'support') and table hyphens do NOT trigger false contradiction warnings.
- Documents with 0 cross-modal pairs return 100.0% consistency with clean empty state.
- Automated tests pass for metric tolerances, keyword boundaries, and AST scans.
