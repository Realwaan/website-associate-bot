# CAP-10 - Pay bills

**Ticket ID:** CAP-10
**Start Date:** 2026-11-23
**Due Date:** 2026-11-25
**Timezone:** Asia/Manila
**Owner Suggestion:** D
**Dependencies:** CAP-07
**Scope:** Required for presentation build

**Dates:** Nov 23-25. **Owner:** D. **Estimate:** 2 days. **Priority:** Must. **Backlog:** EW-09.

## Problem

Pay bills is an original use case missing from the class diagram and source. Add a small seeded bill-payment flow that reuses the tested provider settlement rules.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Offer a small seeded biller list, reference validation, amount entry, fee preview, and PIN confirmation.
2. Reuse provider pending/success/failure handling and duplicate protection.
3. Create bill-payment history, receipt details, and notification; confirmed failure releases reserved funds.

## Acceptance Criteria

- [ ] Offer a small seeded biller list, reference validation, amount entry, fee preview, and PIN confirmation.
- [ ] Reuse provider pending/success/failure handling and duplicate protection.
- [ ] Create bill-payment history, receipt details, and notification; confirmed failure releases reserved funds.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
