# CAP-02 - Persist the wallet domain and transaction rules

**[PRIORITY]**

**Dates:** Nov 10-13. **Owner:** B. **Estimate:** 3 days. **Priority:** Must. **Dependencies:** CAP-01. **Backlog:** EW-02.

## Problem

The OTOG capstone needs this deliverable: persist the wallet domain and transaction rules. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Persist User, Wallet, Transaction, PaymentMethod, and ledger entries with ownership and unique references.
2. Use BigDecimal for money; validate positive amounts and explicit currency precision.
3. Commit balance changes and entries atomically; reject insufficient funds and duplicate requests.
4. Verify restart persistence, rollback on failure, and competing attempts to spend the same funds.

## Acceptance Criteria

- [ ] Persist User, Wallet, Transaction, PaymentMethod, and ledger entries with ownership and unique references.
- [ ] Use BigDecimal for money; validate positive amounts and explicit currency precision.
- [ ] Commit balance changes and entries atomically; reject insufficient funds and duplicate requests.
- [ ] Verify restart persistence, rollback on failure, and competing attempts to spend the same funds.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
