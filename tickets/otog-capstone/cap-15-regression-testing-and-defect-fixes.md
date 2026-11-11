# CAP-15 - Regression testing and defect fixes

**Ticket ID:** CAP-15
**Start Date:** 2026-11-30
**Due Date:** 2026-12-03
**Timezone:** Asia/Manila
**Owner Suggestion:** A and B; module owners fix defects
**Dependencies:** CAP-14
**Scope:** Required for presentation build

**Dates:** Nov 30-Dec 3. **Owners:** A and B; each module owner fixes their defects. **Estimate:** 6 person-days total. **Priority:** Must.

## Problem

The integrated build needs evidence that invalid inputs, retries, concurrency, and restarts do not corrupt financial or authorization state. Fix failures before packaging.

## Potentially Related Files

- `test/com/otog/AtomicCommitAndRollbackTest.java`
- `test/com/otog/BigDecimalMoneyValidationTest.java`
- `test/com/otog/ConcurrencyDoubleSpendTest.java`
- `test/com/otog/RestartPersistenceTest.java` & `test/com/otog/UserWalletPersistenceTest.java`

## What to Fix

1. Test login/OTP/PIN failures, role boundaries, invalid amounts, insufficient funds, duplicate requests, provider timeout, and app restart.
2. Verify every completed payment balances correctly and failed payments do not leave partial updates.
3. Check keyboard navigation, validation messages, and UI responsiveness.
4. Resolve all demo-blocking defects and incorrect balance/security behavior; record remaining cosmetic issues.

## Acceptance Criteria

- [ ] Test login/OTP/PIN failures, role boundaries, invalid amounts, insufficient funds, duplicate requests, provider timeout, and app restart.
- [ ] Verify every completed payment balances correctly and failed payments do not leave partial updates.
- [ ] Check keyboard navigation, validation messages, and UI responsiveness.
- [ ] Resolve all demo-blocking defects and incorrect balance/security behavior; record remaining cosmetic issues.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
