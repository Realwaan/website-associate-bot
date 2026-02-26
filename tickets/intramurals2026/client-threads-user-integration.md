# Integrate user threads into user profile

## Problem

Users currently lack visibility into the threads they have created. A logged-in user should be able to create a thread and have it seamlessly appear on their user profile for easy access and tracking.

## Potentially Related Files

- [components/public/community/new-thread-form.tsx](../app/components/public/community/new-thread-form.tsx) — Thread creation UI
- [actions/thread.ts](../app/actions/thread.ts) — Server actions managing thread creation
- [app/(public)/[username]/profile/page.tsx](../app/app/(public)/[username]/profile/page.tsx) — Profile page displaying the user's data

## What to Fix

1. Ensure the thread creation action in `actions/thread.ts` properly links the new thread to the logged-in user's `authorId`.
2. Update the profile page `page.tsx` to fetch threads with the matching `authorId`.
3. Create a section/tab in the profile page UI to map and render the corresponding threads.

## Acceptance Criteria

- Completed threads properly save the `authorId` relation to the user.
- The user profile page successfully queries the user's created threads.
- The threads appear chronologically structured inside the profile.
