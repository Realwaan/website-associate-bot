# Admin damage report PDF by bbox

## Problem
Admin map cannot export a bounded-region damage report that combines hazard and weather context into a PDF.

## Potentially Related Files
- [OperationsMapPage.tsx](../apps/admin/src/app/map/components/OperationsMapPage.tsx) - bbox interaction source
- [admin-operations.service.ts](../apps/api/src/modules/disaster-response/admin-operations/admin-operations.service.ts) - map/weather aggregation
- [disaster-response.prisma](../apps/api/prisma/schema/models/disaster-response.prisma) - hazard/pin entities

## What to Fix
1. Add admin endpoint accepting bbox and returning PDF
2. Aggregate hazards, warning severity, and weather summary inside bbox
3. Add admin export action from map selection workflow
4. Regenerate API client if endpoint contract changes

## Acceptance Criteria
- Admin can export PDF for selected bbox
- PDF includes hazard counts and weather snapshot
- Export endpoint is restricted to admin role
