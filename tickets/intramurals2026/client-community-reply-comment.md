# Implement Reply-to-Comment Feature in Community

## Problem

Community discussion threads currently do not support replies to individual comments. The infrastructure for thread replies exists in the database (thread_replies table), but the UI and interactions are not implemented.

## Potentially Related Files

- [supabase/migrations/20260216100000_add_threads.sql](../app/supabase/migrations/20260216100000_add_threads.sql) — Lines 14–22: thread_replies table exists
- [supabase/migrations/20260216130001_rls_thread_replies_realtime.sql](../app/supabase/migrations/20260216130001_rls_thread_replies_realtime.sql) — RLS policies for replies
- [actions/thread.ts](../app/actions/thread.ts) — Thread server actions (may need reply actions)
- [components/public/community/](../app/components/public/community/) — Thread components (need reply UI)

## What to Fix

1. Create server action(s) for creating/reading/deleting thread replies
2. Add reply form UI component (text input + avatar/nickname)
3. Display replies under each parent comment in thread
4. Add "Reply" button on each comment to open reply form
5. Style replies with indentation/nesting to show hierarchy
6. Implement Realtime updates for replies (Supabase Postgres Changes subscription)
7. Show reply count on comments

## Acceptance Criteria

- Users can click "Reply" on a comment
- Reply form appears (text input, submit button)
- Reply is created and saved to database
- Replies display under the parent comment
- Reply shows author name and timestamp
- Replies update in real-time for all users
- Can delete own replies (with moderator toggle)
- Mobile-responsive layout for nested replies
