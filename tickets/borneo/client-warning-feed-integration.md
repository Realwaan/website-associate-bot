# Client warning feed integration

## Problem
Mobile warnings screen is not wired to backend warnings, so users can miss active alerts.

## Potentially Related Files
- [Warnings.tsx](../apps/mobile/src/components/screens/Warnings.tsx) - warning UI
- [warnings.controller.ts](../apps/api/src/modules/disaster-response/warnings/warnings.controller.ts) - user warning endpoints
- [api-client.ts](../packages/api-client/src/generated/api-client.ts) - warning hooks

## What to Fix
1. Replace placeholder warning list with `warnings/me` and `warnings/family` query data
2. Render hazard, severity, area, and active time window in cards
3. Add loading, empty, and error states for resilient UX
4. Keep access limited to authenticated users

## Acceptance Criteria
- User sees active warnings from backend data
- Family-impact warnings are distinguishable from personal feed
- Screen handles loading and empty states without crashes
