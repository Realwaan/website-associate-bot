# CAP-08 - History, receipts, and notifications

**Ticket ID:** CAP-08
**Start Date:** 2026-11-19
**Due Date:** 2026-11-27
**Timezone:** Asia/Manila
**Owner Suggestion:** C
**Dependencies:** CAP-02, CAP-06, CAP-07
**Scope:** Required for presentation build

**Dates:** Nov 19-20; extend to new payment types Nov 27. **Owner:** C. **Estimate:** 3 days total. **Priority:** Must. **Backlog:** EW-11, EW-12.

## Problem

Users currently have no persistent history, receipt detail, or notification inbox. Make completed, failed, and pending payments traceable without exposing another account's data.

## Potentially Related Files

- `src/com/otog/model/Transaction.java` & `src/com/otog/model/LedgerEntry.java`
- `src/com/otog/model/ReceiptBuilder.java` (Builder pattern for masked receipts & Prototype repeat-draft helper)
- `src/com/otog/repository/TransactionRepository.java` & `src/com/otog/repository/LedgerRepository.java`
- `src/com/otog/service/WalletService.java`

## What to Fix

1. List owned transactions with date/type/status filters and a receipt detail view.
2. Format receipt details via a ReceiptBuilder (showing amount, fee, reference, counterparty, timestamp, and masked identifiers) and optionally support Prototype-style repeat transaction drafts with a fresh reference number.
3. Persist read/unread notifications after successful commit; notification retries never repeat payments.
4. Verify sender/recipient notifications and account isolation. Printable/exported receipts are stretch scope.

## Acceptance Criteria

- [ ] List owned transactions with date/type/status filters and a receipt detail view.
- [ ] Format receipt details via a ReceiptBuilder (showing amount, fee, reference, counterparty, timestamp, and masked identifiers) and optionally support Prototype-style repeat transaction drafts with a fresh reference number.
- [ ] Persist read/unread notifications after successful commit; notification retries never repeat payments.
- [ ] Verify sender/recipient notifications and account isolation. Printable/exported receipts are stretch scope.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
