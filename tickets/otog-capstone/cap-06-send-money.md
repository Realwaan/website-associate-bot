# CAP-06 - Send money

**Dates:** Nov 16-19. **Owner:** B. **Estimate:** 3 days. **Priority:** Must. **Dependencies:** CAP-02; CAP-04-05 before completion. **Backlog:** EW-07.

## Problem

The OTOG capstone needs this deliverable: send money. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Validate recipient, amount, balance including any fee, and configured limits.
2. Show recipient and total before PIN confirmation.
3. Debit sender and credit recipient atomically; repeated confirmation produces one transfer.
4. Verify success, invalid recipient, insufficient balance, wrong PIN, and failed persistence.

## Acceptance Criteria

- [ ] Validate recipient, amount, balance including any fee, and configured limits.
- [ ] Show recipient and total before PIN confirmation.
- [ ] Debit sender and credit recipient atomically; repeated confirmation produces one transfer.
- [ ] Verify success, invalid recipient, insufficient balance, wrong PIN, and failed persistence.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
