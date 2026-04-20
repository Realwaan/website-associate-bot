# Admin budget tracker portal

## Problem
There is no budget tracking module for disaster operations, preventing admins from monitoring allocation, spending, and remaining funds by category.

## Potentially Related Files
- [disaster-response.module.ts](../apps/api/src/modules/disaster-response/disaster-response.module.ts) - module registration
- [src/app](../apps/admin/src/app) - admin route structure
- [disaster-response.prisma](../apps/api/prisma/schema/models/disaster-response.prisma) - domain schema area

## What to Fix
1. Add budget domain models and migration for allocations and expenses
2. Add admin-only CRUD endpoints and summary analytics service
3. Create admin portal page with category totals and period filters
4. Regenerate API client after OpenAPI updates

## Acceptance Criteria
- Admin can create and update budget categories and entries
- Dashboard shows allocated, spent, and remaining amounts
- Non-admin users cannot access budget APIs or UI
