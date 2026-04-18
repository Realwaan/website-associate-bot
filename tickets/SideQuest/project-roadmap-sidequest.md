# Project Roadmap: SideQuest

**[PRIORITY]**

## Status Snapshot

- Folder: `SideQuest`
- Status: `OPEN`
- Created by: `kesh4809`
- Current scan themes: large-file refactors and debug statement cleanup

## Problem

The current SideQuest backlog is heavily concentrated on oversized modules and leftover debug statements across `app/api`, `components`, and `lib`. Without a phased roadmap, the team risks refactoring conflicts, unstable API behavior, and slower QA verification.

## Potentially Related Files

- `tickets/SideQuest/admin-refactor-large-files-app-api-dashboard.md`
- `tickets/SideQuest/server-refactor-large-files-app-api-assistant.md`
- `tickets/SideQuest/utils-refactor-large-files-lib.md`
- `tickets/SideQuest/client-refactor-large-files-components.md`
- `tickets/SideQuest/client-refactor-large-files-components-ui.md`
- `tickets/SideQuest/admin-refactor-large-files-components.md`
- `tickets/SideQuest/utils-remove-debug-statements-lib.md`
- `tickets/SideQuest/client-remove-debug-statements-components.md`

## What to Fix

1. **Phase 1 - Safety and quick wins (Day 1-2):**
   - Resolve debug cleanup tickets first:
     - `utils-remove-debug-statements-lib.md`
     - `client-remove-debug-statements-components.md`
   - Run smoke tests to ensure logs removed do not hide required operational events.

2. **Phase 2 - API refactor foundation (Day 2-4):**
   - Refactor API-heavy files first because they impact multiple client flows:
     - `admin-refactor-large-files-app-api-dashboard.md`
     - `server-refactor-large-files-app-api-assistant.md`
   - Split route handlers into focused modules (validation, service, response mapping).

3. **Phase 3 - Shared library stabilization (Day 4-5):**
   - Refactor `lib` files to reduce cross-feature coupling:
     - `utils-refactor-large-files-lib.md`
   - Add small unit-level checks for notification and badge logic after split.

4. **Phase 4 - UI refactor and consistency (Day 5-7):**
   - Complete client/admin component split and cleanup:
     - `client-refactor-large-files-components.md`
     - `client-refactor-large-files-components-ui.md`
     - `admin-refactor-large-files-components.md`
   - Keep prop contracts stable to avoid regressions after extraction.

5. **Phase 5 - Validation and closeout (Day 7):**
   - Re-run scanner against SideQuest codebase.
   - Confirm large-file violations are resolved or documented with justification.
   - Convert completed roadmap phases into `/reviewed` and `/closed` ticket workflow.

## Acceptance Criteria

- Debug cleanup tickets are closed before major refactor tickets enter QA.
- API route files are split into smaller modules or include justified exceptions.
- Shared `lib` modules are refactored with no broken imports.
- UI/component refactors preserve existing behavior in key user flows.
- A re-scan produces fewer large-file/debug findings than the current baseline.

---

## Next Feature Roadmap (No Scope Creep)

### Feature: Stale Ticket Reminder Digest

Add a daily digest that highlights tickets stuck in `OPEN`, `CLAIMED`, or `PENDING-REVIEW` longer than a configurable threshold (for example, 48 hours). This keeps momentum high and helps PMs unblock work without adding a new dashboard or changing the core workflow.

### Why This Is The Best Next Feature

- High impact with low risk: it improves execution discipline using data the bot already has.
- No workflow disruption: teams keep the current claim -> review -> close process.
- Fast to ship: mostly query + formatting + one scheduled message path.

### Implementation Tasks

1. Add a DB query helper to return stale tickets by status and age.
2. Add a setting key for stale threshold hours (default: 48).
3. Extend the existing daily summary task to include a "Stale Tickets" section.
4. Include ticket thread mentions and age in hours/days for quick triage.
5. Add a PM command to update threshold (for example `/set-stale-threshold`).
6. Add basic tests for empty, partial, and populated stale-ticket outputs.

### Scope Boundaries

- No new web UI or external dashboard.
- No automatic reassignment, escalation DMs, or role changes.
- No AI prioritization engine.
- No new ticket statuses.
- No changes to developer/QA leaderboard logic.

### Done Criteria

- Daily summary includes stale-ticket section when stale items exist.
- PM can configure threshold without redeploy.
- Output is readable in Discord threads/channels and stays under message limits.
