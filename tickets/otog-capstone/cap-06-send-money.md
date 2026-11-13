# CAP-06 - Send money

**Ticket ID:** CAP-06
**Start Date:** 2026-11-16
**Due Date:** 2026-11-19
**Timezone:** Asia/Manila
**Owner Suggestion:** B
**Dependencies:** CAP-02, CAP-04, CAP-05
**Scope:** Required for presentation build

**Dates:** Nov 16-19. **Owner:** B. **Estimate:** 3 days. **Priority:** Must. **Backlog:** EW-07.

## Problem

SendMoney appears in the class diagram but no source implementation was found. Deliver one complete sender-to-recipient flow that cannot partially debit or double-send.

## Potentially Related Files

- `src/com/otog/model/SendMoneyTransaction.java` & `src/com/otog/model/Transaction.java`
- `src/com/otog/model/TransactionFactory.java` & `src/com/otog/model/TransactionBuilder.java` (Creational Factory/Builder)
- `src/com/otog/service/WalletService.java`
- `src/com/otog/repository/WalletRepository.java` & `src/com/otog/repository/TransactionRepository.java`
- `src/com/otog/exception/InsufficientFundsException.java` & `src/com/otog/exception/DuplicateTransactionException.java`

## What to Fix

1. Validate recipient, amount, balance including any fee, and configured limits.
2. Show recipient and total before PIN confirmation.
3. Construct SendMoneyTransaction via TransactionFactory/TransactionBuilder and debit sender/credit recipient atomically; repeated confirmation produces one transfer.
4. Verify success, invalid recipient, insufficient balance, wrong PIN, and failed persistence.

## Acceptance Criteria

- [ ] Validate recipient, amount, balance including any fee, and configured limits.
- [ ] Show recipient and total before PIN confirmation.
- [ ] Construct SendMoneyTransaction via TransactionFactory/TransactionBuilder and debit sender/credit recipient atomically; repeated confirmation produces one transfer.
- [ ] Verify success, invalid recipient, insufficient balance, wrong PIN, and failed persistence.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
