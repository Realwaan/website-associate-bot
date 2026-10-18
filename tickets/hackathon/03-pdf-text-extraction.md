# 03-pdf-text-extraction.md

## Problem
The product is document-based RAG, so documents must be turned into text with page numbers preserved. Without page numbers, citations are impossible.

## Potentially Related Files
- `app/ingest.py` - extraction (new)
- `pdf_brief_scanner.py` - existing bot code that can be borrowed as reference

## What to Fix
1. Extract text per page from uploaded PDFs using `pypdf`.
2. Return a list of `{doc, page, text}` records.
3. Skip empty pages and log them.
4. OCR fallback only if time remains after the core demo works.

## Acceptance Criteria
- Uploading a 10+ page PDF returns text records, each with the correct page number.
- A text file upload also works.
- Extraction errors show a readable message and do not crash the server.
