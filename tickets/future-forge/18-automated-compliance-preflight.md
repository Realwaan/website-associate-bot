# Automated Compliance Pre-Flight Audit with Negation Detection

**[PRIORITY]**

## Problem
Auditors spend hours manually verifying whether enterprise contracts contain mandatory corporate clauses (uptime SLA, breach penalties, hardware MFA, data security, wire authorization). However, checking topical cosine similarity alone creates a dangerous failure mode: contracts stating 'We provide 0% uptime guarantee and ban MFA' score high cosine similarity to uptime queries and are falsely marked as compliant.

## Potentially Related Files
- `app/audit_scanner.py` - multi-point compliance checklist runner and negation filters
- `app/main.py` - `/compliance-audit` endpoint
- `src/Modals.tsx` - compliance scorecard rendering and property mappings
- `tests/test_pipeline.py` - compliance scanner and negation tests

## What to Fix
1. Define 7 standard corporate compliance controls: Uptime SLA, Breach Penalty, Hardware MFA, Incident Escalation, Dual Wire Auth, Disaster Recovery RTO, and ESG Carbon Offset.
2. In `app/audit_scanner.py`, implement strict negation and disclaimer filters (`0% uptime`, `does not guarantee`, `ban MFA`, `no liability`) mapping them immediately to `GAP` status.
3. Ensure the scanner payload outputs consistent property keys (`clause_excerpt`, `evidence`, `remediation_clause`, `action_plan`) matching frontend modal expectations.
4. Calculate overall compliance readiness percentage score and color-coded status badge (`emerald`, `amber`, or `red`).
5. Render the interactive compliance scorecard modal in the dashboard UI.

## Acceptance Criteria
- Complete 7-point audit executes in under 50 milliseconds without external LLM API calls.
- Contracts with disclaimers or negative clauses are flagged as `GAP` with remediation plans rather than false passes.
- Passing controls display verified excerpt text and section numbers.
- Frontend modal cleanly displays excerpt text without 'Control missing' placeholders.
- Unit tests verify checklist evaluation, negation detection, and scorecard calculations.
