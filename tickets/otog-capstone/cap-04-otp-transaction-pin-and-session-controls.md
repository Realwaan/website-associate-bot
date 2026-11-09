# CAP-04 - OTP, transaction PIN, and session controls

**[PRIORITY]**

**Dates:** Nov 16-18. **Owner:** A. **Estimate:** 3 days. **Priority:** Must. **Dependencies:** CAP-03. **Backlog:** EW-04, EW-05 subset.

## Problem

The OTOG capstone needs this deliverable: otp, transaction pin, and session controls. Complete it in the scheduled window for presentation readiness on December 8, 2026. Verify existing team contributions before duplicating work.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Verify an account-bound OTP with expiry, one-time use, resend cooldown, and attempt limits.
2. Label delivery as simulated; reject random, expired, reused, and another account's codes.
3. Set/change hashed PIN with reauthentication; enforce PIN attempt limits and inactivity timeout.
4. Block outgoing payments without valid PIN authorization. Full account recovery is deferred.

## Acceptance Criteria

- [ ] Verify an account-bound OTP with expiry, one-time use, resend cooldown, and attempt limits.
- [ ] Label delivery as simulated; reject random, expired, reused, and another account's codes.
- [ ] Set/change hashed PIN with reauthentication; enforce PIN attempt limits and inactivity timeout.
- [ ] Block outgoing payments without valid PIN authorization. Full account recovery is deferred.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
