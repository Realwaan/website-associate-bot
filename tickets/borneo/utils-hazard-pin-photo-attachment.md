# Utils hazard pin photo attachment

## Problem
Hazard pins support notes only. Users cannot attach a photo, which reduces triage quality for admins during verification.

## Potentially Related Files
- [disaster-response.prisma](../apps/api/prisma/schema/models/disaster-response.prisma) - extend `MapPinStatus` media fields
- [admin-operations.service.ts](../apps/api/src/modules/disaster-response/admin-operations/admin-operations.service.ts) - pin mapping output
- [api-client.ts](../packages/api-client/src/generated/api-client.ts) - generated request/response types

## What to Fix
1. Add optional `photoUrl` and `photoKey` fields to `MapPinStatus`
2. Add upload flow for pin image and persist media references
3. Include photo metadata in pin DTOs and map overview response
4. Regenerate API client after OpenAPI update

## Acceptance Criteria
- User can submit a pin with optional photo
- Admin receives photo URL with pin data
- Pins without photos still work unchanged
