# Implement Share Button for Community Discussion Threads

## Problem

Community discussion threads need a share button that copies the thread URL to the clipboard, making it easy for users to share discussions on social media or with others.

## Potentially Related Files

- [components/public/community/](../app/components/public/community/) — Community page/thread components
- [app/(public)/community/](../app/app/(public)/community/) — Community page routes
- [actions/thread.ts](../app/actions/thread.ts) — Thread-related server actions
- [lib/utils.ts](../app/lib/utils.ts) — Utility functions (can add copyToClipboard helper)

## What to Fix

1. Add a copy-to-clipboard utility function in `lib/utils.ts` (or use existing)
2. Add share button to thread detail view and/or thread list cards
3. Button should copy thread URL (e.g., `/community/{threadId}`) to clipboard
4. Show toast notification on successful copy (use sonner from shadcn)
5. Icon and styling should match design system

## Acceptance Criteria

- Share button appears on each thread card/detail view
- Clicking share copies thread URL to clipboard
- Toast notification shows "Copied to clipboard"
- URL is the full thread link (not just text)
- Works on desktop and mobile
- Button is accessible (proper labels, keyboard navigation)
