# Implement Import PDF Option for Data Entry

## Problem

Manual data entry for teams, players, or matches is a slow and error-prone process. The user wants an "Import PDF" option to streamline this, allowing admins to upload documents and have the system parse the data for bulk insertion.

## Potentially Related Files

- [lib/admin/export-pdf.ts](../lib/admin/export-pdf.ts) — Existing PDF generation logic (can be used to understand the expected data structure).
- [actions/match.ts](../actions/match.ts) — Server actions for creating matches.
- [actions/team.ts](../actions/team.ts) — Server actions for creating teams.
- [components/admin/matches/matches-data-table.tsx](../components/admin/matches/matches-data-table.tsx) — UI where the "Import" button should be added.
- [components/admin/teams/teams-data-table.tsx](../components/admin/teams/teams-data-table.tsx) — UI where the "Import" button should be added.

## What to Fix

1. **Import UI:**
   - Add an "Import PDF" button to [matches-data-table.tsx](../components/admin/matches/matches-data-table.tsx) and [teams-data-table.tsx](../components/admin/teams/teams-data-table.tsx).
   - Create a modal or upload zone for the PDF file.
   - Show a preview of the parsed data before final submission.

2. **PDF Parsing Logic:**
   - Integrate a library like `pdf-parse` or similar (or use a dedicated OCR service if needed, though simple parsing might suffice).
   - Implement logic to map extracted text to the database schema (e.g., Team Name, Player Name, Student ID).
   - Handle common errors like malformed PDFs or missing data.

3. **Data Insertion:**
   - Create a specialized server action to handle bulk insertion of parsed data.
   - Ensure proper validation and duplicate checking during the process.

## Acceptance Criteria

- Admin can see an "Import PDF" button on Teams and Matches tables.
- Uploading a valid PDF correctly parses the data and shows a preview.
- Admin can confirm the import, which then saves the data to the database.
- Errors are clearly communicated if the PDF cannot be parsed or data is invalid.
- Success notifications are shown after a successful bulk import.
