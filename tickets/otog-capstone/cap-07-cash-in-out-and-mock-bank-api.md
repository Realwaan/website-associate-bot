# CAP-07 - Cash in/out and mock Bank API

**Dates:** Nov 16-20. **Owner:** D. **Estimate:** 4 days. **Priority:** Must. **Dependencies:** CAP-02; CAP-04-05 before completion. **Backlog:** EW-08.

## Problem

The OTOG capstone needs this deliverable: cash in/out and mock bank api. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Link seeded demo bank methods and implement BankApiClient with a mock adapter.
2. Credit cash-in only on success; reserve cash-out funds until settlement, releasing them on confirmed failure.
3. Support success, rejection, and timeout followed by status lookup; unknown outcomes stay pending.
4. Repeated provider responses never duplicate money movement; display provider reference and status.

## Acceptance Criteria

- [ ] Link seeded demo bank methods and implement BankApiClient with a mock adapter.
- [ ] Credit cash-in only on success; reserve cash-out funds until settlement, releasing them on confirmed failure.
- [ ] Support success, rejection, and timeout followed by status lookup; unknown outcomes stay pending.
- [ ] Repeated provider responses never duplicate money movement; display provider reference and status.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
