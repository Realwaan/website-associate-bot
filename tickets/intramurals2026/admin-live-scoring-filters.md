# Implement Comprehensive Filtering for Live Scoring

## Problem

On heavy game days, many matches are played simultaneously. The current admin live scoring interface is limiting as it lacks robust filtering options. Admins need a more comprehensive way to find and manage specific live games, ideally using URL parameters for shareable and bookmarkable filtered views.

## Potentially Related Files

- [app/admin/(dashboard)/live/page.tsx](../app/admin/(dashboard)/live/page.tsx) — Main live scoring page component.
- [components/admin/live/live-scoring-content.tsx](../components/admin/live/live-scoring-content.tsx) — Sub-component rendering the list of live games.
- [lib/scoring-config.ts](../lib/scoring-config.ts) — Configuration for scoring rules and types.
- [actions/match.ts](../actions/match.ts) — Server actions for fetching live matches.

## What to Fix

1. **URL Parameter Support:**
   - Update [live/page.tsx](../app/admin/(dashboard)/live/page.tsx) to read `searchParams` (e.g., `sport`, `venue`, `status`, `date`).
   - Pass these parameters down to the `getLiveMatches` server action or filter the results on the client/server side.

2. **Filter UI Implementation:**
   - Add a filter bar to [live-scoring-content.tsx](../components/admin/live/live-scoring-content.tsx).
   - Include dropdowns or comboboxes for Sport, Venue, and Category.
   - Implement dynamic updates so that selecting a filter updates the URL parameters and refreshes the data.

3. **Comprehensive View:**
   - Ensure the interface remains responsive and clear even with many filtered results.
   - Add a "Clear Filters" option for easy reset.

## Acceptance Criteria

- Admin can filter live games by Sport and Venue.
- Filtering automatically updates the URL (e.g., `/admin/live?sport=Basketball&venue=Gym`).
- Refreshing the page preserves the selected filters.
- The filtering logic is performant and does not cause significant layout shifts.
- "Clear Filters" button successfully resets the view to show all live games.
