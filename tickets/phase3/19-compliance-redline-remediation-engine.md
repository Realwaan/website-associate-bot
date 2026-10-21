# Compliance Redline Remediation Engine and Report Export

**[CRITICAL]**

## Problem
Detecting compliance gaps (missing SLA penalties, lack of hardware MFA, absent disaster recovery RTOs) is only half the commercial audit battle. Enterprise legal teams need pre-approved contract redlines against corporate playbooks. Furthermore, clicking 'Export MD' or 'Download Report' fails with 404 errors if the backend lacks an export endpoint.

## Potentially Related Files
- `app/audit_scanner.py` - compliance check runner and redline playbook definitions
- `app/main.py` - compliance remediation and `/export-report` endpoints
- `src/Modals.tsx` / `app/static/app.js` - redline diff modal and one-click copy cards
- `tests/test_pipeline.py` - compliance scanner and remediation diff verification tests

## What to Fix
1. Define a standardized Enterprise Compliance Remediation Playbook (`COMPLIANCE_REMEDIATION_PLAYBOOK`) mapping each control (SLA-01, PEN-02, SEC-03, INC-04, FIN-05, BCP-06, ESG-07) to pre-approved standard clauses and legal rationales.
2. When a control is flagged as `GAP` or `CAUTION`, generate a unified git-style redline diff (`diff -u` format) showing proposed amendments.
3. Implement `POST /export-report` in `app/main.py` supporting both Markdown and JSON file downloads with proper attachment headers.
4. Add an interactive "View Redline Diff" and "Copy Remediation Clause" button in the frontend Compliance Audit modal.
5. Ensure 100% backward compatibility with existing tests and UI components.

## Acceptance Criteria
- Controls flagged as `GAP` automatically include pre-approved `remediation_clause`, `redline_diff`, and `action_plan`.
- Unified diff cleanly highlights insertions with standard `+ ` markers.
- `POST /export-report` successfully downloads formatted Markdown and JSON audit reports.
- Automated tests verify playbook retrieval, diff generation, and report export.
