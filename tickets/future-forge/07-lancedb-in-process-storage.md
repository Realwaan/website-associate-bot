# 07-lancedb-in-process-storage.md

**[PRIORITY]**

## Problem
External vector databases like Pinecone or Qdrant require Docker containers, external network roundtrips, or cloud API keys that can fail on venue Wi-Fi during a hackathon. We need an embedded, serverless, in-process columnar vector store built on Rust and Apache Arrow that runs locally on disk.

## Potentially Related Files
- `app/vector_store.py` - LanceDB connection, table management, and Arrow records
- `app/config.py` - vector database index directory configuration
- `tests/test_vector_store.py` - LanceDB storage and indexing tests

## What to Fix
1. Initialize an in-process LanceDB database under `data/index/lancedb` without requiring any background daemon.
2. Define a clean table schema storing node ID, vector embedding (384 dimensions), materialized path, text content, image URL, and linked IDs.
3. Use `mode="overwrite"` to support re-indexing documents cleanly.
4. Implement safe table opening guards on Windows to avoid unhandled exceptions if a table does not yet exist.
5. Index both text paragraph leaves and visual crop nodes into a single unified table.

## Acceptance Criteria
- Documents are indexed into LanceDB in under 200 milliseconds without external network calls.
- Windows file access handles tables without memory-map file locking errors.
- Vector search returns top matching records with complete metadata.
- Unit tests pass for database initialization and table operations.
