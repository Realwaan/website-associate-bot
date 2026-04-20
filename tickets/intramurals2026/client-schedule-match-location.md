# Show Match Location with Maps Integration

## Problem

Users need to find exactly where matches are held. Currently, venue names are plain text without map visualization or navigation assistance.

## Potentially Related Files

- [prisma/schema.prisma](../app/prisma/schema.prisma) — Ensure `Venue` has address/location data.
- [components/public/schedule/match-card.tsx](../app/components/public/schedule/match-card.tsx)
- [components/public/schedule/schedule-content.tsx](../app/components/public/schedule/schedule-content.tsx)

## What to Fix

1.  **Data**: Add coordinates or addresses to `Venue` model.
2.  **Maps**: Show an Open Maps pin when clicking a venue location icon.
3.  **Navigation**: Add a "Navigate" button linking to Google Maps for directions.

## Acceptance Criteria

- Map pin appears for match locations using free Open Maps.
- Google Maps navigation link opens correctly on mobile/desktop.
