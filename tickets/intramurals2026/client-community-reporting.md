# Implement Community and Profile Reporting System

## Problem

Users currently have no way to report inappropriate threads, replies, or user profiles. Admins also lack a dedicated interface to review and judge these reports.

## Potentially Related Files

- [prisma/schema.prisma](../app/prisma/schema.prisma) — Need to add `Report` model and relations.
- [actions/report.ts](../app/actions/report.ts) — New server actions for creating reports. [NEW]
- [actions/admin/report.ts](../app/app/admin/actions/report.ts) — New server actions for admin report management. [NEW]
- [components/public/community/thread-item.tsx](../app/components/public/community/thread-item.tsx)
- [components/public/community/reply-item.tsx](../app/components/public/community/reply-item.tsx)
- [app/admin/reports/page.tsx](../app/app/admin/reports/page.tsx) — Admin dashboard for reports. [NEW]

## What to Fix

1.  **Database**: Add `Report` model to `schema.prisma` with `targetType` (THREAD, REPLY, PROFILE).
2.  **Server Actions**: Implement submission and admin judging actions.
3.  **Public UI**: Add report buttons to threads, replies, and profile pages.
4.  **Admin UI**: Create a moderation panel at `/admin/reports` to judge and resolve reports.

## Acceptance Criteria

- Users can report content/profiles.
- Admins can view and judge reports in the dashboard.
- Resolved reports can trigger content hiding or profile flags.
