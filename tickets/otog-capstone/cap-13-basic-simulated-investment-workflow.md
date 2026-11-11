# CAP-13 - Basic simulated investment workflow

**Ticket ID:** CAP-13
**Start Date:** 2026-11-26
**Due Date:** 2026-11-27
**Timezone:** Asia/Manila
**Owner Suggestion:** E
**Dependencies:** CAP-02, CAP-04
**Scope:** Conditional: retain only if required/feasible at November 20 scope gate

**Dates:** Nov 26-27. **Owner:** E. **Estimate:** 2 days. **Priority:** Planned, subject to Nov 20 scope gate. **Backlog:** EW-15 reduced scope.

## Problem

InvestMoney is diagrammed, but no implementation was found. Deliver a single simulated product with atomic purchase/redemption and persisted holdings if retained at the November 20 scope gate.

## Potentially Related Files

- `src/com/otog/model/InvestMoneyTransaction.java` & `src/com/otog/model/TransactionType.java`
- `src/com/otog/repository/TransactionRepository.java`
- `src/com/otog/service/WalletService.java`

## What to Fix

1. Offer one seeded investment product with clearly simulated prices.
2. Preview units and cost; buying debits wallet and increases holdings atomically.
3. Redeeming credits wallet and decreases holdings atomically; reject insufficient funds and overselling.
4. Persist holdings and activity. Defer live prices, forecasting, and multiple product types.

## Acceptance Criteria

- [ ] Offer one seeded investment product with clearly simulated prices.
- [ ] Preview units and cost; buying debits wallet and increases holdings atomically.
- [ ] Redeeming credits wallet and decreases holdings atomically; reject insufficient funds and overselling.
- [ ] Persist holdings and activity. Defer live prices, forecasting, and multiple product types.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
