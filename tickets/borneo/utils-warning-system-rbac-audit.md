# Utils warning system RBAC audit

## Problem
Warning features exist, but admin access is partly enforced in frontend only.

## Potentially Related Files
- [admin-operations.controller.ts](../apps/api/src/modules/disaster-response/admin-operations/admin-operations.controller.ts) - admin routes
- [auth-session.guard.ts](../apps/api/src/modules/auth/guards/auth-session.guard.ts) - current session guard
- [shell.tsx](../apps/admin/src/app/shell.tsx) - client-side admin gate

## What to Fix
1. Enforce admin role authorization on warning/admin endpoints server-side
2. Add tests for unauthorized and forbidden access scenarios
3. Standardize audit log fields for warning create/update/cancel actions
4. Document schema impact explicitly in module notes

## Acceptance Criteria
- Non-admin requests to admin warning APIs are forbidden server-side
- Admin warning actions produce consistent audit logs
- Authorization tests cover success and failure paths
