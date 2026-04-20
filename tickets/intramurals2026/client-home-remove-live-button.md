# Remove Live Button from Frontend

## Problem

The "Live" badge/button in the frontend is no longer required and should be removed for a cleaner UI.

## Potentially Related Files

- [components/public/home/hero-section.tsx](../app/components/public/home/hero-section.tsx)
- [app/app/(public)/page.tsx](../app/app/(public)/page.tsx)

## What to Fix

1.  **UI**: Remove the `liveCount` badge from `HeroSection`.
2.  **Cleanup**: Remove unnecessary live count fetching from the home page component.

## Acceptance Criteria

- "Live" badge is no longer visible in the hero section.
- UI layout remains intact.
