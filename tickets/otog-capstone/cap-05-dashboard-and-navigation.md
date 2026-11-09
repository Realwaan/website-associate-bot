# CAP-05 - Dashboard and navigation

**Ticket ID:** CAP-05
**Start Date:** 2026-11-11
**Due Date:** 2026-11-18
**Timezone:** Asia/Manila
**Owner Suggestion:** C
**Dependencies:** CAP-01, CAP-02, CAP-03, CAP-04
**Scope:** Required for presentation build

**Dates:** Nov 11-13; authenticated integration Nov 18. **Owner:** C. **Estimate:** 2 days. **Priority:** Must. **Backlog:** EW-06.

## Problem

Successful login currently ends with a dialog. Users need a dashboard that displays their own wallet and navigates to working payment features.

## Potentially Related Files

- [OTOG source](F:/OTOG/src/) - Java application; confirm new module paths during implementation.
- [One-month plan](../../OTOG-one-month-ticket-plan.md) - schedule, roles, dependencies, and scope gates.

## What to Fix

1. Show signed-in user's balance, recent activity, logout, and feature navigation.
2. Refresh after payments; display useful empty, loading, and failure states.
3. Keep database/provider work off the Swing UI thread; hide unfinished features from the final demo.

## Acceptance Criteria

- [ ] Show signed-in user's balance, recent activity, logout, and feature navigation.
- [ ] Refresh after payments; display useful empty, loading, and failure states.
- [ ] Keep database/provider work off the Swing UI thread; hide unfinished features from the final demo.

## Delivery Context

Use simulated financial integrations. Owner letters are proposed roles, not assigned Discord users. Presentations: December 9 (F1), December 10 (F2), December 12 (G9), 2026. Feature freeze: November 29. Readiness deadline: December 8.
