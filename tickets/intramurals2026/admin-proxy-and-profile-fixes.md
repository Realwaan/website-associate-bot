# Fix Admin Proxy Restrictions and Own Profile Visibility

## Problem

Admins currently face access limitations when trying to view public sections of the application, such as the community tab. This is likely due to restrictive logic in the proxy or middleware that handles authentication and routing. Additionally, there is a known issue where admins cannot properly view their own profile page.

## Potentially Related Files

- [proxy.ts](../proxy.ts) — Main proxy utility used in middleware.
- [lib/supabase/middleware.ts](../lib/supabase/middleware.ts) — Session and role-based redirect logic.
- [app/(public)/[username]/profile/page.tsx](../app/(public)/[username]/profile/page.tsx) — Profile view page where visibility issues occur.

## What to Fix

1. **Proxy/Middleware Adjustments:**
   - Review [proxy.ts](../proxy.ts) and [middleware.ts](../lib/supabase/middleware.ts) to identify rules that block ADMIN roles from accessing public routes.
   - Adjust the `updateSession` logic to ensure that an "ADMIN" role is granted at least the same access level as a "USER" for public routes.
   - Ensure that the proxy does not inadvertently rewrite or block admin requests to community and other user-facing features.

2. **Admin Profile Visibility:**
   - Investigate [profile/page.tsx](../app/(public)/[username]/profile/page.tsx) to see why the admin's own profile might not be loading.
   - Fix any logic that prevents the profile from being fetched when the logged-in user is an admin.
   - Test by navigating to `/admin` and then to the admin's own public profile URL.

## Acceptance Criteria

- Admin can access and interact with the Community Tab without being redirected or blocked.
- Admin can view their own public profile page at `/[username]/profile`.
- No new security vulnerabilities are introduced (e.g., users gaining admin access).
- Proxy logic remains robust against bot probes while allowing legitimate admin traffic.
