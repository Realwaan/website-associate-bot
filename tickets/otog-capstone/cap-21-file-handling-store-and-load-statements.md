# CAP-21 - Add Java file handling to store and load wallet statements

**Ticket ID:** CAP-21
**Start Date:** 2026-11-20
**Due Date:** 2026-11-27
**Timezone:** Asia/Manila
**Owner Suggestion:** C with E
**Dependencies:** CAP-02, CAP-08
**Scope:** Required for presentation build

**Dates:** Nov 20-27. **Owner:** C, with E. **Estimate:** 2 days. **Priority:** Must.

## Problem

The CSIT227 Capstone Requirements allocate `5% + bonus 5%` to File Handling (*"store and load data into the program"*), but the codebase currently only uses SQLite JDBC with no Java file I/O (`BufferedWriter` / `BufferedReader`) store-and-load workflow.

## Potentially Related Files

- `src/com/otog/service/StatementFileService.java`
- `src/com/otog/ui/OverviewPanel.java` & `src/com/otog/ui/OverviewPanel.form`
- `src/com/otog/ui/Main.java`
- `test/com/otog/SwingFormsAndFileHandlingTest.java`

## What to Fix

1. Implement `StatementFileService` using `try-with-resources` `BufferedWriter` and `BufferedReader` to store (export) and load (import) masked wallet statements and transaction receipts.
2. Add Export Statement and Load Statement actions to the dashboard (`OverviewPanel` / `Main`) using `JFileChooser` and off-EDT `SwingWorker` tasks.
3. Validate imported statement files and throw domain exceptions (`OtogException`) on malformed or tampered files without corrupting wallet state.
4. Add automated JUnit 5 tests covering store/load round-trips, identifier masking, and malformed file rejection.

## Acceptance Criteria

- [ ] Implement `StatementFileService` using `try-with-resources` `BufferedWriter` and `BufferedReader` to store (export) and load (import) masked wallet statements and transaction receipts.
- [ ] Add Export Statement and Load Statement actions to the dashboard (`OverviewPanel` / `Main`) using `JFileChooser` and off-EDT `SwingWorker` tasks.
- [ ] Validate imported statement files and throw domain exceptions (`OtogException`) on malformed or tampered files without corrupting wallet state.
- [ ] Add automated JUnit 5 tests covering store/load round-trips, identifier masking, and malformed file rejection.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026 (12 minutes max). GitHub link submission in MS Teams (`jayvince.serato@cit.edu`): December 1. Feature freeze: November 29. Readiness deadline: December 8.
