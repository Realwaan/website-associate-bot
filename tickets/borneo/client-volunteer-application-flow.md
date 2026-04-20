# Client volunteer application flow

## Problem
Volunteer APIs exist, but mobile help screen still lacks a complete application UX.

## Potentially Related Files
- [HelpDashboard.tsx](../apps/mobile/src/components/screens/HelpDashboard.tsx) - volunteer CTA
- [volunteers.controller.ts](../apps/api/src/modules/disaster-response/volunteers/volunteers.controller.ts) - apply/status APIs
- [api-client.ts](../packages/api-client/src/generated/api-client.ts) - volunteer hooks

## What to Fix
1. Add mobile volunteer application modal/form with notes and validation
2. Wire submit to existing `useVolunteersControllerApply` hook
3. Show current application/profile status states in help screen
4. Handle duplicate pending applications with clear feedback

## Acceptance Criteria
- Authenticated user can submit volunteer application from mobile
- Existing pending/approved state is shown on screen
- Duplicate submits do not create inconsistent records
