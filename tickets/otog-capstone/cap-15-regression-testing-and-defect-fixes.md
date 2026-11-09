# CAP-15 - Regression testing and defect fixes

**Dates:** Nov 30-Dec 3. **Owners:** A and B; each module owner fixes their defects. **Estimate:** 6 person-days total. **Priority:** Must. **Dependencies:** CAP-14.

## Problem

The OTOG capstone needs this deliverable: regression testing and defect fixes. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

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
