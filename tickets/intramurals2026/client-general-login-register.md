# Implement Login/Register Feature

**[PRIORITY]**

## Problem

Currently, the application has a Supabase auth setup with profile management infra, but no public-facing login/register UI. Users cannot create accounts or authenticate.

## Potentially Related Files

- [lib/supabase/server.ts](../app/lib/supabase/server.ts) — Supabase service role client
- [lib/supabase/middleware.ts](../app/lib/supabase/middleware.ts) — Session management
- [supabase/migrations/20260214080014_add_profiles.sql](../app/supabase/migrations/20260214080014_add_profiles.sql) — Profile/RBAC setup
- [supabase/config.toml](../app/supabase/config.toml#L103) — Auth configuration (signup enabled, JWT config)
- [app/admin/login/](../app/app/admin/login/) — Reference for auth UI pattern (may have existing login form)

## What to Fix

1. Create login/register page(s) — component(s) with email/password forms
2. Add Zod validation schema for signup (email, password, password confirm)
3. Create server action(s) for `signUp()` and `signIn()`
4. Implement session sync after auth (cookies, Supabase session)
5. Add logout button/action (likely in navbar or account menu)
6. Protect admin routes — require session + ADMIN role
7. Add auth state to navbar (show username or login button)

## Acceptance Criteria

- Users can sign up with email/password on public page
- Users can log in with credentials
- Session persists across page navigation (cookies)
- Admin routes require ADMIN role
- Logout clears session
- Navbar shows username when logged in
- "PRIORITY: HIGH" — blocks other features
