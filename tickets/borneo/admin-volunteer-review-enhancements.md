# Admin volunteer review enhancements

## Problem
Admin can approve/reject volunteer applications, but decision detail is too shallow.

## Potentially Related Files
- [VolunteerApprovalsPage.tsx](../apps/admin/src/app/volunteers/components/VolunteerApprovalsPage.tsx) - UI
- [admin-operations.controller.ts](../apps/api/src/modules/disaster-response/admin-operations/admin-operations.controller.ts) - review endpoint
- [admin-operations.service.ts](../apps/api/src/modules/disaster-response/admin-operations/admin-operations.service.ts) - review logic

## What to Fix
1. Require reason on reject and optional note on approve
2. Display review history in volunteer approvals page
3. Persist actor, status change, and reason consistently
4. Keep endpoint admin-only and regenerate API client if needed

## Acceptance Criteria
- Rejections require a reason before submit
- Decision history is visible to admins
- Review audit data is complete and queryable
