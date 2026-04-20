# Utils user profile pregnant age group

## Problem
User profile lacks pregnancy status and age group fields, so risk targeting cannot account for vulnerable demographics during disasters.

## Potentially Related Files
- [auth.prisma](../apps/api/prisma/schema/models/auth.prisma) - `User` model fields
- [auth.controller.ts](../apps/api/src/modules/auth/auth.controller.ts) - profile/session payload surface
- [api-client.ts](../packages/api-client/src/generated/api-client.ts) - generated auth types

## What to Fix
1. Add nullable `pregnantStatus` and `ageGroup` fields to `User` with migration
2. Add authenticated profile update endpoint and DTO validation
3. Expose new fields in session/profile responses and mobile profile UI
4. Regenerate API client: `npm run api:client:generate`

## Acceptance Criteria
- User can save and fetch pregnant status and age group
- Existing users migrate safely with null defaults
- Invalid age-group values are rejected by validation
