# 04-chunking-and-embedding-index.md

## Problem
Extracted pages are too large to retrieve precisely. We need chunks with metadata and a searchable vector index.

## Potentially Related Files
- `app/chunking.py`, `app/index.py` (new)

## What to Fix
1. Split page text into chunks of roughly 500 characters with 50 overlap, keeping `doc` and `page` metadata.
2. Embed chunks locally with `fastembed` (BGE-small), or via the ALMA API if an embedding endpoint is provided.
3. Store vectors in a numpy array and chunk metadata in JSON under `data/index/`.
4. Rebuild the index on each upload.

## Acceptance Criteria
- Indexing a 20-page PDF finishes in under 30 seconds.
- Each chunk keeps its source document and page number.
- The index reloads from disk after a server restart.
