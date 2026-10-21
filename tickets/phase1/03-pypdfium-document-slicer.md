# 03-pypdfium-document-slicer.md

**[PRIORITY]**

## Problem
Standard PDF readers either extract flat text without layout awareness or choke on multi-page enterprise documents. In addition, C-FFI bindings to PDFium can leak native unmanaged memory and file descriptors on Windows if documents are not explicitly closed, causing `[WinError 32]` file access conflicts.

## Potentially Related Files
- `app/ingest.py` - PDF extraction, text normalization, and page preview generator
- `app/config.py` - preview storage paths and rendering constants
- `tests/test_pipeline.py` - document ingestion and chunking tests

## What to Fix
1. Integrate `pypdfium2` as the native C++ PDF engine for sub-second layout parsing.
2. Implement smart page preview rendering: render up to 10 pages upfront and provide lazy on-demand rendering for 300+ page documents.
3. Wrap all `pypdfium2.PdfDocument` instances in deterministic `try...finally: pdf.close()` blocks to release C memory immediately.
4. Convert raw extracted text into structured Markdown headers (`##`, `###`) and formatted bullet lists.
5. Save page previews in compressed WebP format (quality 80) to save disk space and accelerate browser rendering.

## Acceptance Criteria
- PDF pages are extracted into clean Markdown in under 1.5 seconds for a 20-page document.
- Zero open file locks remain on the PDF file after preview rendering.
- WebP previews render sharply without browser distortion or missing headers.
- Unit tests verify both small and large document preview pathways.\n