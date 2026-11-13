# CAP-04 - OTP, transaction PIN, and session controls

**Ticket ID:** CAP-04
**Start Date:** 2026-11-16
**Due Date:** 2026-11-18
**Timezone:** Asia/Manila
**Owner Suggestion:** A
**Dependencies:** CAP-03
**Scope:** Required for presentation build

**[PRIORITY]**

**Dates:** Nov 16-18. **Owner:** A. **Estimate:** 3 days. **Priority:** Must. **Backlog:** EW-04, EW-05 subset.

## Problem

The current second-factor check accepts any nonempty text and no transaction PIN service exists. Require verified, expiring challenges and protected payment authorization.

## Potentially Related Files

- `src/UserLogin.java` & `src/UserLogin.form`
- `src/com/otog/model/User.java`
- `src/com/otog/repository/UserRepository.java`
- `src/com/otog/service/WalletService.java`
- `src/com/otog/service/SessionManager.java` (Singleton session & inactivity state)

## What to Fix

1. Verify an account-bound OTP with expiry, one-time use, resend cooldown, and attempt limits.
2. Label delivery as simulated; reject random, expired, reused, and another account's codes.
3. Set/change hashed PIN with reauthentication; enforce PIN attempt limits and inactivity timeout via the Singleton SessionManager.
4. Block outgoing payments without valid PIN authorization. Full account recovery is deferred.

## Acceptance Criteria

- [ ] Verify an account-bound OTP with expiry, one-time use, resend cooldown, and attempt limits.
- [ ] Label delivery as simulated; reject random, expired, reused, and another account's codes.
- [ ] Set/change hashed PIN with reauthentication; enforce PIN attempt limits and inactivity timeout via the Singleton SessionManager.
- [ ] Block outgoing payments without valid PIN authorization. Full account recovery is deferred.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
