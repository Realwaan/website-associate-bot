# CAP-17 - Package and verify the release candidate

**Ticket ID:** CAP-17
**Start Date:** 2026-12-02
**Due Date:** 2026-12-04
**Timezone:** Asia/Manila
**Owner Suggestion:** C with D
**Dependencies:** CAP-15, CAP-16
**Scope:** Required for presentation build

**Dates:** Dec 2-4. **Owner:** C, with D. **Estimate:** 2 days. **Priority:** Must.

## Problem

A developer-machine build is not sufficient for laboratory presentation. Package and validate an offline-capable release on the actual presentation laptop with recoverable demo data.

## Potentially Related Files

- `build.bat`, `run.bat`, `test.bat`
- `lib/forms_rt.jar` & `lib/sqlite-jdbc-3.47.0.0.jar`
- `src/com/otog/database/DatabaseManager.java`
- `README.md`

## What to Fix

1. Package a runnable release with required runtime/dependencies and documented launch instructions.
2. Test installation/launch on the presentation laptop without relying on the developer IDE.
3. Provide a resettable demo database, QR sample, release backup, screenshots, and a short backup demo recording.
4. Verify the classroom demonstration can run offline using simulated integrations.
5. Label the Dec 4 release candidate and record its commit/build identifier.

## Acceptance Criteria

- [ ] Package a runnable release with required runtime/dependencies and documented launch instructions.
- [ ] Test installation/launch on the presentation laptop without relying on the developer IDE.
- [ ] Provide a resettable demo database, QR sample, release backup, screenshots, and a short backup demo recording.
- [ ] Verify the classroom demonstration can run offline using simulated integrations.
- [ ] Label the Dec 4 release candidate and record its commit/build identifier.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
