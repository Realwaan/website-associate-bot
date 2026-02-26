# Add success confirmation message after verifying email

## Problem

After a user clicks the link in their email to confirm their account, there is no explicit success message confirming the action to the user on the redirected page. Users might be confused if their email verification went through successfully.

## Potentially Related Files

- [app/(public)/auth/confirm/route.ts](../app/app/(public)/auth/confirm/route.ts) — Route handler for the Supabase email confirmation callback.
- [app/(public)/page.tsx](../app/app/(public)/page.tsx) OR the redirect destination page (e.g., login or home).

## What to Fix

1. In the auth confirmation flow (either the route handler or the page it redirects to), detect the successful confirmation of the email.
2. Pass a URL parameter (e.g., `?verified=true`) if redirecting from a route handler.
3. On the destination page, read the URL parameter and trigger a success toast (e.g., "Email successfully confirmed! You can now log in.") using the application's notification system.

## Acceptance Criteria

- When a user verifies their email via the magic link, they see a clear success toast or banner upon landing back in the app.
- The message only appears once immediately following the confirmation.
