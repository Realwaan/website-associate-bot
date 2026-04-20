# Implement Match Mentions in Community Posts

## Problem

There is no way to formally mention or link a match in community discussions, making it hard to reference specific upcoming or past games.

## Potentially Related Files

- [components/public/community/thread-editor.tsx](../app/components/public/community/thread-editor.tsx)
- [actions/match.ts](../app/actions/match.ts)
- [components/public/community/content-renderer.tsx](../app/components/public/community/content-renderer.tsx) [NEW]

## What to Fix

1.  **Selector**: Add a verbose match selector to the thread editor.
2.  **Mention Format**: Use a specific syntax (e.g., `[match:id]`) to store mentions.
3.  **Rendering**: Update the content renderer to display mentions as clickable match cards or links.

## Acceptance Criteria

- Users can select and mention a match in posts.
- Match selector is verbose (Teams, Sport, Date).
- Mentions render as links/cards in the public view.
