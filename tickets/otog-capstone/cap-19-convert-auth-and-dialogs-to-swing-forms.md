# CAP-19 - Convert auth and dialog screens to IntelliJ Swing forms

**Ticket ID:** CAP-19
**Start Date:** 2026-11-18
**Due Date:** 2026-11-22
**Timezone:** Asia/Manila
**Owner Suggestion:** A with C
**Dependencies:** CAP-01, CAP-03, CAP-04
**Scope:** Required for presentation build

**[PRIORITY]**

**Dates:** Nov 18-22. **Owner:** A, with C. **Estimate:** 2 days. **Priority:** Must.

## Problem

Only `UserLogin` currently has an IntelliJ GUI Designer `.form` file, and its labels are out of sync with `UserLogin.java`, while `RegisterDialog` and the Transaction PIN dialog are hardcoded inside Java classes. Convert auth and dialog screens to bound `.form` files and stage all `.form` files in the build.

## Potentially Related Files

- `src/UserLogin.java` & `src/UserLogin.form`
- `src/com/otog/ui/RegisterDialog.java` & `src/com/otog/ui/RegisterDialog.form`
- `src/com/otog/ui/PinSettingsDialog.java` & `src/com/otog/ui/PinSettingsDialog.form`
- `build.bat` & `.idea/uiDesigner.xml`

## What to Fix

1. Synchronize `src/UserLogin.form` with `src/UserLogin.java` (`$$$setupUI$$$()`) and refine login and 2FA visual spacing and headers.
2. Convert `src/com/otog/ui/RegisterDialog.java` from hardcoded `GridLayout` to a bound IntelliJ Swing form (`src/com/otog/ui/RegisterDialog.form`) with `GridLayoutManager` and `$$$setupUI$$$()`.
3. Extract the inline Transaction PIN dialog from `Main` into `src/com/otog/ui/PinSettingsDialog.java` and `src/com/otog/ui/PinSettingsDialog.form` with off-EDT `SwingWorker` execution.
4. Update `build.bat` to copy all `src/**/*.form` files into matching package directories under `out/production/OTOG/`.

## Acceptance Criteria

- [ ] Synchronize `src/UserLogin.form` with `src/UserLogin.java` (`$$$setupUI$$$()`) and refine login and 2FA visual spacing and headers.
- [ ] Convert `src/com/otog/ui/RegisterDialog.java` from hardcoded `GridLayout` to a bound IntelliJ Swing form (`src/com/otog/ui/RegisterDialog.form`) with `GridLayoutManager` and `$$$setupUI$$$()`.
- [ ] Extract the inline Transaction PIN dialog from `Main` into `src/com/otog/ui/PinSettingsDialog.java` and `src/com/otog/ui/PinSettingsDialog.form` with off-EDT `SwingWorker` execution.
- [ ] Update `build.bat` to copy all `src/**/*.form` files into matching package directories under `out/production/OTOG/`.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026 (12 minutes max). GitHub link submission in MS Teams (`jayvince.serato@cit.edu`): December 1. Feature freeze: November 29. Readiness deadline: December 8.
