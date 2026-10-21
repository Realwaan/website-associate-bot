# Multi-Format Ingestion and Document Slicer

**[PRIORITY]**

## Problem
Enterprises and audit teams handle multiple document formats beyond PDFs, including Word contracts (.docx), PowerPoint architecture briefings (.pptx), markdown specs (.md), and plain text SOPs (.txt). Limiting ingestion strictly to PDF leaves critical enterprise collateral unsearchable. In addition, C-FFI bindings to PDFium can leak unmanaged memory on Windows if documents are not explicitly closed, causing [WinError 32] file locking conflicts.

## Potentially Related Files
- app/ingest.py - multi-format file extraction, text normalization, and page preview generator
- app/config.py - preview storage paths and rendering constants
- tests/test_pipeline.py - multi-format document ingestion and chunking tests

## What to Fix
1. Integrate pypdfium2 as the native C++ PDF engine with deterministic try...finally: pdf.close() blocks to prevent Windows file descriptor leaks.
2. Integrate python-docx to extract structured headings, tables, and paragraphs from Microsoft Word documents (.docx).
3. Integrate python-pptx to extract slide titles, bullet points, and speaker notes from PowerPoint presentations (.pptx).
4. Implement UTF-8 multi-encoding fallback for plain text (.txt) and Markdown (.md) documents.
5. Generate compressed WebP page previews (quality 80) for visual inspection in the UI.
6. Convert extracted text across all formats into structured Markdown headers and clean bullet lists.

## Acceptance Criteria
- Uploading PDF, DOCX, PPTX, TXT, or MD documents successfully parses text and constructs chunks.
- Zero open file locks remain on uploaded files after preview rendering.
- Ingestion executes in under 2 seconds for a standard 20-page document.
- Unit tests verify ingestion for all supported file formats.
