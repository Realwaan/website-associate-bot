# Add 'Show Password' toggle on registration form

## Problem

Users registering for an account cannot view the password they are typing. Adding a "Show Password" toggle prevents typos and improves the user experience during sign-up.

## Potentially Related Files

- [components/auth/register-form.tsx](../app/components/auth/register-form.tsx) — The UI component for registration.

## What to Fix

1. Add a local state boolean `showPassword` to `register-form.tsx`.
2. Add an eye icon (e.g., from `lucide-react`) inside or next to the password input field.
3. Toggle the input `type` between `"password"` and `"text"` based on the state.

## Acceptance Criteria

- A visibility toggle icon appears inside the password field on the registration form.
- Clicking the toggle alternates between hiding and showing the password text in plain text.
- The default state is hidden (`type="password"`).
