# CAP-07 - Cash in/out and mock Bank API

**Ticket ID:** CAP-07
**Start Date:** 2026-11-16
**Due Date:** 2026-11-20
**Timezone:** Asia/Manila
**Owner Suggestion:** D
**Dependencies:** CAP-02, CAP-04, CAP-05
**Scope:** Required for presentation build

**Dates:** Nov 16-20. **Owner:** D. **Estimate:** 4 days. **Priority:** Must. **Backlog:** EW-08.

## Problem

CashInOut appears in the diagram but no funding adapter or settlement implementation was found. Demonstrate cash in/out with a deterministic mock Bank API, including failed and uncertain outcomes.

## Potentially Related Files

- `src/com/otog/model/CashInOutTransaction.java` & `src/com/otog/model/PaymentMethod.java`
- `src/com/otog/repository/PaymentMethodRepository.java` & `src/com/otog/repository/TransactionRepository.java`
- `src/com/otog/service/WalletService.java`
- `src/com/otog/service/PaymentProviderFactory.java` (Factory / Abstract Factory for mock bank providers)

## What to Fix

1. Link seeded demo bank methods and implement BankApiClient with a mock adapter and PaymentProviderFactory (Factory/Abstract Factory for deterministic success/failure/timeout modes).
2. Credit cash-in only on success; reserve cash-out funds until settlement, releasing them on confirmed failure.
3. Support success, rejection, and timeout followed by status lookup; unknown outcomes stay pending.
4. Repeated provider responses never duplicate money movement; display provider reference and status.

## Acceptance Criteria

- [ ] Link seeded demo bank methods and implement BankApiClient with a mock adapter and PaymentProviderFactory (Factory/Abstract Factory for deterministic success/failure/timeout modes).
- [ ] Credit cash-in only on success; reserve cash-out funds until settlement, releasing them on confirmed failure.
- [ ] Support success, rejection, and timeout followed by status lookup; unknown outcomes stay pending.
- [ ] Repeated provider responses never duplicate money movement; display provider reference and status.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
