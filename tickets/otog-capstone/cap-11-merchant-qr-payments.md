# CAP-11 - Merchant QR payments

**Dates:** Nov 19-25. **Owner:** E. **Estimate:** 4 days. **Priority:** Must. **Dependencies:** CAP-06, CAP-09; CAP-08 for activity integration. **Backlog:** EW-10.

## Problem

The OTOG capstone needs this deliverable: merchant qr payments. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Seed a merchant profile; generate and import QR images using a documented project format.
2. Validate merchant, currency, and amount; show recipient confirmation before PIN approval.
3. Reuse the atomic transfer service; merchant sees received payments.
4. Reject malformed/inactive-merchant QR codes and duplicate submissions. Camera scanning and real-provider QR compatibility are excluded.

## Acceptance Criteria

- [ ] Seed a merchant profile; generate and import QR images using a documented project format.
- [ ] Validate merchant, currency, and amount; show recipient confirmation before PIN approval.
- [ ] Reuse the atomic transfer service; merchant sees received payments.
- [ ] Reject malformed/inactive-merchant QR codes and duplicate submissions. Camera scanning and real-provider QR compatibility are excluded.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
