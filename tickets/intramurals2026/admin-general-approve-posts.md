# Implement Community Post Approval System for Admin

## Problem

Community threads are currently posted anonymously without moderation. The admin dashboard should have a post approval system to review and approve/reject community discussions before they appear publicly.

## Potentially Related Files

- [supabase/migrations/20260216100000_add_threads.sql](../app/supabase/migrations/20260216100000_add_threads.sql) — Threads table (add is_approved field if not present)
- [actions/thread.ts](../app/actions/thread.ts) — Thread server actions (add approval actions)
- [components/admin/](../app/components/admin/) — Admin dashboard components (create new thread moderation panel)
- [app/admin/(dashboard)/](../app/app/admin/(dashboard)/) — Admin routes (add threads page)

## What to Fix

1. Add `is_approved` boolean field to threads table (if not present)
2. Update thread creation flow — default to `is_approved = false`
3. Create server actions:
   - `approveThread(threadId)` — mark as approved
   - `rejectThread(threadId)` — mark as rejected/deleted
   - `getPendingThreads()` — fetch unapproved threads
4. Create admin moderation panel with list of pending posts
5. Show thread preview, author IP hash (for tracking spam), and action buttons
6. Hide unapproved threads from public community view (filter in queries)

## Acceptance Criteria

- Admin can see pending threads in a dashboard
- Admin can approve thread (makes it visible)
- Admin can reject thread (hides from public)
- Approved threads appear in community section
- Unapproved threads are invisible to public users
- Notification/badge shows pending count
- Thread shows approval status in admin view
