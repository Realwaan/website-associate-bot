# CAP-03 - Registration and password authentication

**[PRIORITY]**

**Dates:** Nov 11-13. **Owner:** A. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-01; CAP-02 before integration. **Backlog:** EW-03.

## Problem

The OTOG capstone needs this deliverable: registration and password authentication. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Register a unique account and create its wallet; replace hardcoded credentials with salted password hashes.
2. Reject incorrect passwords and duplicate account identifiers; enforce failed-login limits.
3. Protect authenticated screens and clear session state on logout.

## Acceptance Criteria

- [ ] Register a unique account and create its wallet; replace hardcoded credentials with salted password hashes.
- [ ] Reject incorrect passwords and duplicate account identifiers; enforce failed-login limits.
- [ ] Protect authenticated screens and clear session state on logout.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
