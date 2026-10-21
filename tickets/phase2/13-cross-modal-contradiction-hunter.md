# 13-cross-modal-contradiction-hunter.md

**[CRITICAL]**

## Problem
A major source of corporate fraud, compliance failures, and medical errors is discrepancies between prose claims and embedded charts (e.g., text claims "+15% growth", but the linked table shows a -2% loss or footnote discrepancy). No existing RAG tool audits documents for cross-modal self-contradiction.

## Potentially Related Files
- `app/discrepancy_scanner.py` - heuristic rules and LLM contradiction detection
- `app/main.py` - full document scan API endpoint `/api/discrepancies`
- `tests/test_discrepancy_scanner.py` - heuristic and end-to-end scanner tests

## What to Fix
1. Implement local deterministic heuristic pattern detection: growth claims vs negative/decline visual keywords, and numerical percentage discrepancies (>2.0% delta).
2. Implement deep verification using Gemma 4 to compare author text against table descriptions and return JSON verdict (`ALIGN`, `CAUTION`, `CONTRADICTION`).
3. Ensure the scanner falls back to heuristic checks if the LLM endpoint times out or is unreachable.
4. Calculate document consistency score and flag verdict (`CONSISTENT`, `CAUTION`, or `FLAGGED`).
5. Ensure empty ASTs or documents with zero cross-modal pairs return 100.0% consistency rather than 0%.

## Acceptance Criteria
- Blatant contradictions (e.g., text claims 99.9% uptime, footnote table shows 98.2%) are immediately flagged with `CONTRADICTION`.
- Heuristic fallback operates in under 10ms with zero network calls.
- In-memory consistency report contains exact numerical deltas and citations.
- 100% test coverage on heuristic rules and end-to-end AST scans.\n