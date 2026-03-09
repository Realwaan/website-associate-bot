# Client volunteer home location and routing

## Problem
Volunteers see straight-line paths from GPS only. No "own place" representation or road routing exists, making response planning from a home base impossible.

## Potentially Related Files
- [MapComponent.tsx](../apps/mobile/src/components/MapComponent.tsx)
- [disaster-response.prisma](../apps/api/prisma/schema/models/disaster-response.prisma)
- [HelpDashboard.tsx](../apps/mobile/src/components/screens/HelpDashboard.tsx)

## What to Fix
1. Add `baseLatitude`/`baseLongitude` to `VolunteerProfile`
2. Add "Set Home" in Profile screen
3. Render "Home" icon in `MapComponent`
4. Use Leaflet Routing Machine for road paths
5. Add "Route from Current/Home" toggle

## Acceptance Criteria
- Volunteer can set and see "own place"
- Map shows road routes with ETA
- Toggle between GPS/Home routing works
- Map fits route bounds
