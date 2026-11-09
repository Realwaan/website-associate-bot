# CAP-14 - Integration checkpoint and feature freeze

**Dates:** Nov 23-27; freeze Nov 29. **Owner:** B, with C. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-06-11; CAP-12-13 if retained.

## Problem

The OTOG capstone needs this deliverable: integration checkpoint and feature freeze. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Merge reviewed features into one runnable build and exercise cross-feature balance/history consistency.
2. Prepare deterministic user, merchant, admin, biller, and bank demo data.
3. Complete the original sequence: send money, validate, update both balances, deliver notifications.
4. Confirm no new features after Nov 29; unresolved work becomes a bug or explicitly deferred scope.

## Acceptance Criteria

- [ ] Merge reviewed features into one runnable build and exercise cross-feature balance/history consistency.
- [ ] Prepare deterministic user, merchant, admin, biller, and bank demo data.
- [ ] Complete the original sequence: send money, validate, update both balances, deliver notifications.
- [ ] Confirm no new features after Nov 29; unresolved work becomes a bug or explicitly deferred scope.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
