# CAP-09 - Admin permissions and account controls

**Dates:** Nov 16-18. **Owner:** E. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-02, CAP-03. **Backlog:** EW-13.

## Problem

The OTOG capstone needs this deliverable: admin permissions and account controls. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Seed an admin account and enforce User/Merchant/Admin permissions in services.
2. View accounts/transactions and suspend/reactivate users with a recorded reason.
3. Suspended accounts cannot initiate payments; record admin actions without secrets.
4. Ordinary users cannot invoke admin operations or inspect another user's history; prohibit direct balance editing.

## Acceptance Criteria

- [ ] Seed an admin account and enforce User/Merchant/Admin permissions in services.
- [ ] View accounts/transactions and suspend/reactivate users with a recorded reason.
- [ ] Suspended accounts cannot initiate payments; record admin actions without secrets.
- [ ] Ordinary users cannot invoke admin operations or inspect another user's history; prohibit direct balance editing.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
