# Client family addition account gated flow

## Problem
Family APIs support create/join, but mobile does not complete the account-gated flow.

## Potentially Related Files
- [Family.tsx](../apps/mobile/src/components/screens/Family.tsx) - family UI
- [families.controller.ts](../apps/api/src/modules/disaster-response/families/families.controller.ts) - create/join APIs
- [auth.tsx](../apps/admin/src/lib/auth.tsx) - session usage reference

## What to Fix
1. Add create family and join-by-code forms in mobile family screen
2. Gate actions behind authenticated session and show login prompt otherwise
3. Render real family member map/list data from `families/me/map`
4. Add duplicate join and invalid code handling messages

## Acceptance Criteria
- Authenticated user can create or join a family from mobile
- Unauthenticated user cannot perform family mutation actions
- Family members list/map updates after successful join
