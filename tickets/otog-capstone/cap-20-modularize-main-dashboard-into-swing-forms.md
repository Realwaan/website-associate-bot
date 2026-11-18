# CAP-20 - Modularize Main dashboard into Swing form panels

**Ticket ID:** CAP-20
**Start Date:** 2026-11-19
**Due Date:** 2026-11-26
**Timezone:** Asia/Manila
**Owner Suggestion:** C with B
**Dependencies:** CAP-05, CAP-06, CAP-07, CAP-09, CAP-19
**Scope:** Required for presentation build

**[PRIORITY]**

**Dates:** Nov 19-26. **Owner:** C, with B. **Estimate:** 3 days. **Priority:** Must.

## Problem

`src/com/otog/ui/Main.java` has grown beyond 2,300 lines with all dashboard tabs hardcoded in Java rather than bound IntelliJ GUI Designer `.form` files. Modularize the dashboard shell and tabs into `.form`-backed Swing panels that are neat and suitable for manual code inspection.

## Potentially Related Files

- `src/com/otog/ui/Main.java` & `src/com/otog/ui/Main.form`
- `src/com/otog/ui/OverviewPanel.java` & `src/com/otog/ui/OverviewPanel.form`
- `src/com/otog/ui/CashInOutPanel.java` & `src/com/otog/ui/CashInOutPanel.form`
- `src/com/otog/ui/SendMoneyPanel.java` & `src/com/otog/ui/SendMoneyPanel.form`
- `src/com/otog/ui/AdminControlsPanel.java` & `src/com/otog/ui/AdminControlsPanel.form`

## What to Fix

1. Bind `src/com/otog/ui/Main.java` to `src/com/otog/ui/Main.form` for the top-level dashboard shell (header, tabbed navigation, status footer) with `$$$setupUI$$$()`.
2. Extract hardcoded tab builders from `Main.java` into dedicated `.form`-backed panel classes (`OverviewPanel`, `CashInOutPanel`, `SendMoneyPanel`, `AdminControlsPanel`).
3. Apply neat, consistent Swing visual styling (typography, padding, borders, table sizing) for the CSIT227 GUI rubric (`[15%]`) while keeping `INSTRUMENT_CLASSES=false` compatibility.
4. Preserve all existing `Main` public component getters, `SwingWorker` off-EDT execution, and service interface boundaries so all JUnit 5 UI tests pass.

## Acceptance Criteria

- [ ] Bind `src/com/otog/ui/Main.java` to `src/com/otog/ui/Main.form` for the top-level dashboard shell (header, tabbed navigation, status footer) with `$$$setupUI$$$()`.
- [ ] Extract hardcoded tab builders from `Main.java` into dedicated `.form`-backed panel classes (`OverviewPanel`, `CashInOutPanel`, `SendMoneyPanel`, `AdminControlsPanel`).
- [ ] Apply neat, consistent Swing visual styling (typography, padding, borders, table sizing) for the CSIT227 GUI rubric (`[15%]`) while keeping `INSTRUMENT_CLASSES=false` compatibility.
- [ ] Preserve all existing `Main` public component getters, `SwingWorker` off-EDT execution, and service interface boundaries so all JUnit 5 UI tests pass.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026 (12 minutes max). GitHub link submission in MS Teams (`jayvince.serato@cit.edu`): December 1. Feature freeze: November 29. Readiness deadline: December 8.
