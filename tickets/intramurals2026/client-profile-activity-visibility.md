# Show user activity when profile is not private

## Problem

Currently, a user's threads, likes, and comments are not visible to other users on their profile page. We want to display this activity so long as the user's profile is not set to private (`isPrivate` = false).

## Potentially Related Files

- [app/(public)/[username]/profile/page.tsx](../app/app/(public)/[username]/profile/page.tsx) — Main profile page component.
- [actions/profile.ts](../app/actions/profile.ts) — Server actions fetching the profile data (needs to include relational data for threads, likes, replies).

## What to Fix

1. Update `getProfileByUsername` in `actions/profile.ts` or add a new action to fetch the user's recent threads, likes, and replies from the database.
2. In `app/(public)/[username]/profile/page.tsx`, ensure we check `if (!profile.isPrivate || isOwner)` before displaying the activity.
3. Design and implement a new "Activity" or "History" tab/section in the profile UI to render the fetched data.

## Acceptance Criteria

- Public profiles show the user's recent threads, likes, and comments.
- Private profiles (`isPrivate = true`) completely hide this activity from viewers, showing only the locked UI.
- The profile owner can still view their own activity even if the profile is set to private.
