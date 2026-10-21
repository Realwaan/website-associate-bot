# Hybrid RRF Retrieval Engine with LanceDB Fusion

**[CRITICAL]**

## Problem
Vector search alone struggles with exact keyword queries (acronyms, clause numbers like 'Section 4.2', monetary sums), while BM25 keyword search fails on semantic paraphrasing. Furthermore, `rank_bm25` throws `ZeroDivisionError` when initialized with empty documents, and failing to fuse LanceDB vector hits leaves persistent index records unused.

## Potentially Related Files
- `app/retriever.py` - BM25 lexical + dense vector Reciprocal Rank Fusion (RRF)
- `app/vector_store.py` - LanceDB vector search candidate generator
- `app/embeddings.py` - FastEmbed query embedding with unit length normalization
- `tests/test_systems_edge_cases.py` - empty corpus and retrieval boundary tests

## What to Fix
1. Guard `HybridRetriever.__init__` against empty chunk lists to prevent `ZeroDivisionError` on empty or image-only documents.
2. Implement BM25 Okapi lexical scoring over tokenized child sentence chunks.
3. Implement dense vector dot product scoring against pre-normalized unit embeddings.
4. Query `LANCE_STORE.search()` and blend LanceDB vector candidates with in-memory dense and lexical scores using Reciprocal Rank Fusion: `RRF = sum(1.0 / (k_rrf + rank))` with `k_rrf = 60`.
5. Deduplicate parent paragraph contexts so multiple matching sentences from the same paragraph merge into a single coherent citation.

## Acceptance Criteria
- Hybrid retrieval finishes in under 10 milliseconds across document chunks.
- LanceDB vector hits actively influence RRF ranking alongside BM25 and dense in-memory scores.
- Both exact clause numbers ('Section 4.1') and semantic concepts retrieve relevant passages.
- Empty document corpus returns an empty list without raising `ZeroDivisionError`.
