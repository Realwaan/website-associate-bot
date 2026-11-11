# CAP-11 - Merchant QR payments

**Ticket ID:** CAP-11
**Start Date:** 2026-11-19
**Due Date:** 2026-11-25
**Timezone:** Asia/Manila
**Owner Suggestion:** E
**Dependencies:** CAP-06, CAP-09
**Scope:** Required for presentation build

**Dates:** Nov 19-25. **Owner:** E. **Estimate:** 4 days. **Priority:** Must. **Backlog:** EW-10.

## Problem

The Merchant actor and QR payment use case are not represented by working code. Deliver a project-specific QR image import flow with recipient confirmation and a merchant receipt view.

## Potentially Related Files

- `src/com/otog/model/User.java` & `src/com/otog/model/UserRole.java`
- `src/com/otog/model/SendMoneyTransaction.java`
- `src/com/otog/service/WalletService.java`

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
