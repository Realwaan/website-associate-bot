# CAP-03 - Registration and password authentication

**Ticket ID:** CAP-03
**Start Date:** 2026-11-11
**Due Date:** 2026-11-13
**Timezone:** Asia/Manila
**Owner Suggestion:** A
**Dependencies:** CAP-01, CAP-02
**Scope:** Required for presentation build

**[PRIORITY]**

**Dates:** Nov 11-13. **Owner:** A. **Estimate:** 2 days. **Priority:** Must. **Backlog:** EW-03.

## Problem

UserLogin currently compares input with hardcoded admin/password credentials. Implement per-user registration and password authentication before exposing private wallet screens.

## Potentially Related Files

- `src/UserLogin.java` & `src/UserLogin.form`
- `src/com/otog/model/User.java` & `src/com/otog/model/UserStatus.java`
- `src/com/otog/repository/UserRepository.java`
- `src/com/otog/service/WalletService.java`
- `src/com/otog/service/SessionManager.java` (Singleton session holder)

## What to Fix

1. Register a unique account and create its wallet; replace hardcoded credentials with salted password hashes.
2. Reject incorrect passwords and duplicate account identifiers; enforce failed-login limits.
3. Protect authenticated screens using a Singleton SessionManager (`SessionManager.getInstance()`) and clear session state on logout.

## Acceptance Criteria

- [ ] Register a unique account and create its wallet; replace hardcoded credentials with salted password hashes.
- [ ] Reject incorrect passwords and duplicate account identifiers; enforce failed-login limits.
- [ ] Protect authenticated screens using a Singleton SessionManager (`SessionManager.getInstance()`) and clear session state on logout.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
