# Implement Scannable PDF Export for Match Results

## Problem

Admin users need a way to generate and download scandable PDFs of match results for record-keeping, printing, or distribution. Currently, no PDF export functionality exists.

## Potentially Related Files

- [components/admin/matches/](../app/components/admin/matches/) — Match management UI in admin
- [actions/match.ts](../app/actions/match.ts) — Match server actions (can add PDF export action)
- [lib/admin/export-pdf.ts](../app/lib/admin/export-pdf.ts) — PDF export utility (may already exist)
- [components/ui/button.tsx](../app/components/ui/button.tsx) — Button component for export triggers

## What to Fix

1. Install PDF library (e.g., `pdfkit`, `jsPDF`, or `html2pdf`) if not already present
2. Create server action `exportMatchResultsPDF()` in actions/match.ts
3. Add export button to match results view/table in admin
4. Generate PDF with:
   - Match details (teams, score, date, venue)
   - QR code (optional but "scannable" feature)
   - Tournament info/branding
5. Make PDF downloadable via button click
6. Support single match or batch export

## Acceptance Criteria

- Admin can click "Export PDF" button on match record
- PDF downloads with match details and scores
- PDF includes scannable element (QR code linking to match or tournament)
- PDF is formatted professionally with branding
- File naming is clear (e.g., `match-results-2026-02-21.pdf`)
- Works for single or multiple matches
- No errors during PDF generation
