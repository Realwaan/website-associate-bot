# Admin hazard pin approval workflow

## Problem
Admin map renders hazard pins but lacks a clear approve/reject workflow.

## Potentially Related Files
- [OperationsMapPage.tsx](../apps/admin/src/app/map/components/OperationsMapPage.tsx) - pin review UI
- [admin-operations.controller.ts](../apps/api/src/modules/disaster-response/admin-operations/admin-operations.controller.ts) - admin endpoints
- [disaster-response.prisma](../apps/api/prisma/schema/models/disaster-response.prisma) - pin status model

## What to Fix
1. Add admin-only endpoint to review pin status with reason/note
2. Add review controls in admin map drawer for selected pin
3. Store reviewer and review timestamp for auditability
4. Regenerate API client after contract changes

## Acceptance Criteria
- Admin can approve or reject a submitted pin
- Review reason and actor are persisted
- Non-admin users cannot access review endpoint
