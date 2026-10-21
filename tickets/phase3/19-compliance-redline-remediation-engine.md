# 19-compliance-redline-remediation-engine.md

**[CRITICAL]**

## Problem
Detecting compliance gaps (missing SLA penalties, lack of hardware MFA, absent disaster recovery RTOs) is only half the commercial audit battle. Enterprise legal teams waste hours writing replacement clauses and negotiating redlines against non-compliant vendor paper. Commercial platforms like Robin AI and Ironclad command high valuations because they automatically generate contract redlines against corporate playbooks.

## Potentially Related Files
- `app/audit_scanner.py` - compliance check runner and redline playbook definitions
- `app/main.py` - compliance remediation endpoints
- `app/static/index.html` - redline diff modal and one-click copy cards
- `app/static/app.js` - compliance scorecard rendering with interactive diff viewer
- `tests/test_pipeline.py` - compliance scanner and remediation diff verification tests

## What to Fix
1. Define a standardized Enterprise Compliance Remediation Playbook (`COMPLIANCE_REMEDIATION_PLAYBOOK`) mapping each control (SLA-01, PEN-02, SEC-03, INC-04, FIN-05, BCP-06, ESG-07) to pre-approved standard clauses and legal rationales.
2. When a control is flagged as `GAP` or `CAUTION`, generate a unified git-style redline diff (`diff -u` format) showing the exact proposed insertion/amendment into the contract.
3. Expose the redline diffs and action plans directly in `run_compliance_audit()` output and via `GET /compliance-audit`.
4. Add an interactive "View Redline Diff" and "Copy Remediation Clause" button in the frontend Compliance Audit modal.
5. Ensure 100% backward compatibility with existing tests and UI components.

## Acceptance Criteria
- Controls flagged as `GAP` automatically include pre-approved `remediation_clause`, `redline_diff`, and `action_plan`.
- Unified diff cleanly highlights insertions with standard `+ ` markers.
- Passing controls indicate compliant status without generating redundant diffs.
- Automated tests verify playbook retrieval, diff generation, and scorecard calculations.\n