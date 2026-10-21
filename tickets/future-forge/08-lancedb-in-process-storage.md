# LanceDB In-Process Vector Indexing and Search Integration

**[CRITICAL]**

## Problem
In-memory vector lists do not persist across restarts and lack high-performance columnar indexing. However, if LanceDB is only written to during upload and `LANCE_STORE.search()` is never called in production queries, the vector database becomes write-only dead code. Furthermore, attaching sentence-chunk embeddings to AST leaf nodes corrupts the index and pads trailing nodes with `[0.0] * 384` zeros.

## Potentially Related Files
- `app/vector_store.py` - LanceDB connection, 1:1 leaf embedding table, and search methods
- `app/main.py` - document upload indexing loop and query pipeline integration
- `app/retriever.py` - hybrid retrieval fusing LanceDB vector candidates
- `tests/test_vector_store.py` - LanceDB storage, alignment, and search verification tests

## What to Fix
1. Initialize an in-process LanceDB database under `data/index/lancedb` without external background daemons.
2. In `app/main.py` upload pipeline, generate 1:1 text embeddings specifically for AST leaf nodes so every stored record vector matches its text content without zero-padding corruption.
3. Define table schema storing node ID, 384-dimension vector embedding, materialized path, text content, image URL, and linked node IDs.
4. Connect `LANCE_STORE.search()` directly into the hybrid retrieval pipeline so LanceDB vector candidates are actively ranked and returned.
5. In `GET /health`, dynamically query `LANCE_STORE.db.list_tables()` to verify database health instead of returning a hardcoded boolean.

## Acceptance Criteria
- Documents are indexed into LanceDB with 1:1 aligned embeddings and zero dummy padding.
- `LANCE_STORE.search()` is actively invoked during query execution and returns top matching AST leaves.
- `GET /health` reports true database status by checking existing tables.
- Unit tests verify LanceDB indexing, search ranking, and health diagnostics.
