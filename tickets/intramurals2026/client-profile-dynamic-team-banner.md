# Dynamic Profile Banner based on Rooting Team

## Problem

The header background for the user profile is currently a static red/gradient (`bg-gradient-to-r from-[#97170e] to-[#c41e12]`). We want this banner to dynamically change its color or image based on the specific team the user is rooting for.

## Potentially Related Files

- [app/(public)/[username]/profile/page.tsx](../app/app/(public)/[username]/profile/page.tsx) — The profile page rendering the avatar and banner.
- [lib/data/queries.ts](../app/lib/data/queries.ts) (or team definitions) — To pull team-specific colors/assets.

## What to Fix

1. Define a mapping of Team IDs to specific colors or banner images (either in the database or via a frontend configuration file).
2. Inside `app/(public)/[username]/profile/page.tsx`, check `profile.rootingForTeamId`.
3. Swap out the static `className="... bg-gradient-to-r from-[#97170e] to-[#c41e12] ..."` with a dynamically computed class or inline style corresponding to the team's colors.

## Acceptance Criteria

- If a user roots for Team A, the profile banner uses Team A's colors/banner.
- If a user roots for Team B, the profile banner dynamically updates to Team B's colors/banner.
- If no team is selected, a fallback default gradient is implemented.
