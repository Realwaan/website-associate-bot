# Client hazard pin text submission

## Problem
Mobile users cannot submit hazard pins. Admin can only view existing pin statuses.

## Potentially Related Files
- [HelpDashboard.tsx](../apps/mobile/src/components/screens/HelpDashboard.tsx) - reporting entry
- [disaster-response.prisma](../apps/api/prisma/schema/models/disaster-response.prisma) - `MapPinStatus` model
- [admin-operations.controller.ts](../apps/api/src/modules/disaster-response/admin-operations/admin-operations.controller.ts) - current read-only pin API

## What to Fix
1. Add authenticated `POST /api/pins` for text + hazard type + lat/lng submission
2. Add DTO validation and persist reporter relation to `MapPinStatus`
3. Add mobile form flow to submit pin
4. Regenerate API client if OpenAPI changes

## Acceptance Criteria
- Authenticated user can submit hazard pin text with location
- New pin appears in admin map overview
- Invalid payloads are rejected with clear errors
