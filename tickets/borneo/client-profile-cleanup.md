# client-profile-cleanup.md

## Problem
The Profile page currently contains several inactive menu items: "Notification Settings", "Security & Privacy", "Your Contributions", and "General Settings". These clutter the UI and provide no current functionality, leading to a suboptimal user experience.

## Potentially Related Files
- [Profile.tsx](../apps/mobile/src/components/screens/Profile.tsx#L78-L83) - Current implementation of the Profile menu items

## What to Fix
1. Modify the `menuItems` array in `Profile.tsx`.
2. Remove the following objects from the array:
    - Notification Settings
    - Security & Privacy
    - Your Contributions
    - General Settings
3. Any other unused icons or styles related specifically to these menu items should also be removed if applicable.

## Acceptance Criteria
- Profile screen no longer displays the 4 removed menu items.
- Remaining elements (User Info, Demographic checkboxes, Set Home location, and Log Out button) stay functional.
- The layout remains clean and properly padded.
