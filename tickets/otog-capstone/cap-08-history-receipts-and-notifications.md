# CAP-08 - History, receipts, and notifications

**Dates:** Nov 19-20; extend to new payment types Nov 27. **Owner:** C. **Estimate:** 3 days total. **Priority:** Must. **Dependencies:** CAP-02, CAP-06; CAP-07 for funding records. **Backlog:** EW-11, EW-12.

## Problem

The OTOG capstone needs this deliverable: history, receipts, and notifications. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. List owned transactions with date/type/status filters and a receipt detail view.
2. Show amount, fee, reference, counterparty, timestamp, and status; mask private account identifiers.
3. Persist read/unread notifications after successful commit; notification retries never repeat payments.
4. Verify sender/recipient notifications and account isolation. Printable/exported receipts are stretch scope.

## Acceptance Criteria

- [ ] List owned transactions with date/type/status filters and a receipt detail view.
- [ ] Show amount, fee, reference, counterparty, timestamp, and status; mask private account identifiers.
- [ ] Persist read/unread notifications after successful commit; notification retries never repeat payments.
- [ ] Verify sender/recipient notifications and account isolation. Printable/exported receipts are stretch scope.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
