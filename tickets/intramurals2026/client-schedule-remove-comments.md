# Remove Match Comments from Schedule View

## Problem

The schedule page currently displays a match comment sheet/dialog with real-time comments feature. This feature should be removed entirely from the schedule view and related components.

## Potentially Related Files

- [components/public/schedule/match-comment-sheet.tsx](../app/components/public/schedule/match-comment-sheet.tsx) — Entire match comments component
- [components/public/schedule/schedule-content.tsx](../app/components/public/schedule/schedule-content.tsx) — Main schedule display (imports MatchCommentSheet)
- [actions/comment.ts](../app/actions/comment.ts) — Comment-related server actions (can delete)
- [supabase/migrations/20260216074351_add_match_comments.sql](../app/supabase/migrations/20260216074351_add_match_comments.sql) — match_comments table (can leave in DB for now)

## What to Fix

1. Remove `MatchCommentSheet` import from schedule-content.tsx
2. Remove the "Comments" button/trigger from the match card UI in schedule
3. Delete or deprecate the entire `match-comment-sheet.tsx` component
4. Remove comment-related server actions from `actions/comment.ts` (or mark deprecated)
5. Update schedule content to no longer reference comments

## Acceptance Criteria

- No comment button/icon appears on match cards in schedule
- No comment sheet/modal opens when clicking matches
- Schedule view loads without errors
- "Comments" label/indicator removed from match card
