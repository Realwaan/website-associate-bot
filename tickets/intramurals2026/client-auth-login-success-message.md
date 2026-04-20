# Add successful login confirmation message

## Problem

After a user correctly inputs their credentials and logs in, they are redirected or the modal closes, but there is no explicit visual feedback confirming that the login was successful.

## Potentially Related Files

- [components/auth/login-form.tsx](../app/components/auth/login-form.tsx) — The client component handling login submission.

## What to Fix

1. In `login-form.tsx`, inside the successful branch of the submit handler, trigger a success notification before or right after acting on the successful authentication.
2. Use the application's existing toast/notification library (e.g., `sonner` via `toast.success`).

## Acceptance Criteria

- Upon successful login, a toast/notification appears stating "Successfully logged in".
- The message uses the app's standard notification UI.
