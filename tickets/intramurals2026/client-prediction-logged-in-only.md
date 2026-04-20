# Implement a Prediction Feature only if the user is logged in

## Problem

Currently, the prediction feature might be accessible or visible to users who are not logged in, or the application needs this exact feature to be restricted to authenticated users solely. Anonymous users should be prompted to log in before they can make predictions.

## Potentially Related Files

- [actions/prediction.ts](../app/actions/prediction.ts) — Server actions for handling predictions.
- [components/public/schedule/match-detail-sheet.tsx](../app/components/public/schedule/match-detail-sheet.tsx) — UI for the match details where prediction takes place.
- [components/auth/auth-modal.tsx](../app/components/auth/auth-modal.tsx) — To prompt unauthenticated users.

## What to Fix

1. Update `match-detail-sheet.tsx` to check for an active user session before allowing interaction with the prediction feature.
2. If unauthenticated, clicking the prediction button should trigger the `auth-modal.tsx` (login prompt).
3. Ensure `actions/prediction.ts` is verifying session/user ID securely so unauthorized requests are rejected at the server level.

## Acceptance Criteria

- The prediction interaction is disabled or triggers a login modal for guests.
- Logged-in users can successfully submit predictions.
- Server-side validation explicitly blocks anonymous API submissions.
