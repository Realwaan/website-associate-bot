# Admin population density by bbox

## Problem
Admin map lacks population density analytics for selected areas, limiting response prioritization.

## Potentially Related Files
- [OperationsMapPage.tsx](../apps/admin/src/app/map/components/OperationsMapPage.tsx) - map layer integration
- [admin-operations.controller.ts](../apps/api/src/modules/disaster-response/admin-operations/admin-operations.controller.ts) - analytics endpoint surface
- [providers](../apps/api/src/providers) - external data provider integration

## What to Fix
1. Add admin endpoint to compute/query population density by bbox
2. Integrate population data provider with caching
3. Add density layer toggle and legend in admin map UI
4. Regenerate API client after endpoint addition

## Acceptance Criteria
- Admin can request density metrics for selected bbox
- Map renders density layer with readable legend values
- Endpoint and UI are accessible only to admin users
