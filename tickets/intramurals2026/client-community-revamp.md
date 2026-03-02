# Revamp Community Tab: Remove Nicknames and Add Tag Caching

## Problem

The Community Tab currently allows users to post using optional nicknames, which can lead to anonymous or unaccountable behavior. Additionally, the lack of data caching for community threads results in unnecessary database queries and potentially stale content. The user wants to:
1. Remove the nickname option entirely.
2. Implement tag-based caching using Next.js `revalidateTag`.
3. Ensure the author's real username or nickname (if still stored in profile) is visible on all threads and replies.

## Potentially Related Files

- [actions/thread.ts](../actions/thread.ts) — Server actions for fetching and creating threads/replies.
- [components/public/community/new-thread-form.tsx](../components/public/community/new-thread-form.tsx) — Form for creating new threads.
- [components/public/community/thread-detail.tsx](../components/public/community/thread-detail.tsx) — Thread detail view.
- [components/public/community/thread-list.tsx](../components/public/community/thread-list.tsx) — List view for threads.
- [lib/hooks/use-nickname.ts](../lib/hooks/use-nickname.ts) — Hook managing nickname state.

## What to Fix

1. **Remove Nickname Option:**
   - Modify [new-thread-form.tsx](../components/public/community/new-thread-form.tsx) to remove the checkbox or toggle for "Post as Nickname".
   - Update the form schema to exclude the nickname field.
   - Deprecate or remove [use-nickname.ts](../lib/hooks/use-nickname.ts) if it's no longer used.

2. **Implement Tag Caching:**
   - In [actions/thread.ts](../actions/thread.ts), wrap thread and reply fetch functions with `next: { tags: ['community-threads', 'community-replies'] }`.
   - Add `revalidateTag('community-threads')` to the thread creation server action.
   - Add `revalidateTag('community-replies')` to the reply creation server action.
   - Reference: [Next.js revalidateTag](https://nextjs.org/docs/app/api-reference/functions/revalidateTag)

3. **Author Visibility:**
   - Ensure the `getThreads` and `getThreadById` actions in [actions/thread.ts](../actions/thread.ts) include the author's profile data (username, display name).
   - Update [thread-list.tsx](../components/public/community/thread-list.tsx) and [thread-detail.tsx](../components/public/community/thread-detail.tsx) to display the author's username or full name instead of an optional nickname.

## Acceptance Criteria

- No nickname option is visible when creating a new thread or reply.
- Threads and replies show the author's actual username or name.
- Creating a thread or reply immediately updates the list/detail view via `revalidateTag`.
- Navigating to the community page uses cached data when appropriate, improving performance.
