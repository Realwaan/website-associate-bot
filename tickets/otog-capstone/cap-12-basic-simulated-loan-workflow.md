# CAP-12 - Basic simulated loan workflow

**Ticket ID:** CAP-12
**Start Date:** 2026-11-26
**Due Date:** 2026-11-27
**Timezone:** Asia/Manila
**Owner Suggestion:** D
**Dependencies:** CAP-02, CAP-04, CAP-09
**Scope:** Conditional: retain only if required/feasible at November 20 scope gate

**Dates:** Nov 26-27. **Owner:** D. **Estimate:** 2 days. **Priority:** Planned, subject to Nov 20 scope gate. **Backlog:** EW-14 reduced scope.

## Problem

Loan is diagrammed, but no implementation was found. Deliver a small simulated application, approval, single disbursement, and full-repayment lifecycle if retained at the November 20 scope gate.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Offer one configured loan product with documented interest/fee calculation and total repayment preview.
2. User applies; admin approves/rejects; approval credits the wallet exactly once.
3. Show amount due and support full repayment with atomic wallet/loan updates.
4. Reject duplicate disbursement, insufficient-funds repayment, and repeat repayment of a paid loan.
5. Defer installment scheduling, partial repayment, penalties, and advanced eligibility scoring.

## Acceptance Criteria

- [ ] Offer one configured loan product with documented interest/fee calculation and total repayment preview.
- [ ] User applies; admin approves/rejects; approval credits the wallet exactly once.
- [ ] Show amount due and support full repayment with atomic wallet/loan updates.
- [ ] Reject duplicate disbursement, insufficient-funds repayment, and repeat repayment of a paid loan.
- [ ] Defer installment scheduling, partial repayment, penalties, and advanced eligibility scoring.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
