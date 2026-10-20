# 16-automated-compliance-preflight.md

**[PRIORITY]**

## Problem
Auditors spend hours manually verifying whether enterprise contracts contain mandatory corporate clauses (uptime SLA, breach penalties, hardware MFA, data security, wire authorization). Demonstrating an automated 7-point pre-flight compliance audit instantly wins business relevance points.

## Potentially Related Files
- `app/audit_scanner.py` - multi-point compliance checklist runner
- `app/main.py` - `/compliance-audit` endpoint
- `tests/test_pipeline.py` - compliance scanner tests

## What to Fix
1. Define standard corporate compliance checks: Uptime SLA, Breach Penalty, Hardware MFA, Incident Escalation, Dual Wire Auth, Disaster Recovery RTO, and ESG Carbon Offset.
2. Run in-memory hybrid retrieval for each check in under 40 milliseconds total.
3. Classify each clause as `PASS` (verified excerpt found) or `GAP` (mandatory clause missing).
4. Calculate overall compliance readiness percentage score and color-coded status badge (`emerald`, `amber`, or `red`).
5. Render the interactive compliance scorecard modal in the dashboard UI.

## Acceptance Criteria
- Complete 7-point audit executes in under 50 milliseconds without external LLM API calls.
- Missing clauses are highlighted in red as high-risk gaps with clear recommendations.
- Passing clauses display verified section numbers and page links.
- Unit tests verify checklist evaluation and scorecard calculations.
