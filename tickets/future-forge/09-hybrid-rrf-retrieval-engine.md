# 09-hybrid-rrf-retrieval-engine.md

**[CRITICAL]**

## Problem
Vector search alone struggles with exact keyword queries (acronyms, clause numbers like "Section 4.2", monetary sums), while BM25 keyword search fails on semantic paraphrasing. Furthermore, `rank_bm25` throws an unhandled `ZeroDivisionError: division by zero` when initialized with an empty document or image-only corpus.

## Potentially Related Files
- `app/retriever.py` - BM25 lexical + dense vector Reciprocal Rank Fusion (RRF)
- `app/embeddings.py` - FastEmbed query embedding with unit length normalization
- `tests/test_systems_edge_cases.py` - empty corpus and retrieval boundary tests

## What to Fix
1. Guard `HybridRetriever.__init__` against empty chunk lists to prevent `ZeroDivisionError` on image-only documents.
2. Implement BM25 Okapi lexical scoring over tokenized child sentence chunks.
3. Implement dense vector dot product scoring against pre-normalized unit embeddings.
4. Merge rankings using Reciprocal Rank Fusion formula: `RRF = sum(1.0 / (k_rrf + rank))` with `k_rrf = 60`.
5. Deduplicate parent paragraph contexts so multiple matching sentences from the same paragraph merge into a single coherent citation.

## Acceptance Criteria
- Hybrid retrieval finishes in under 5 milliseconds on 100+ document chunks.
- Both exact clause numbers ("Section 4.1") and semantic concepts ("liability limits") retrieve relevant passages.
- Empty document corpus returns an empty list without raising `ZeroDivisionError`.
- Unit tests verify reciprocal rank fusion scoring and parent deduplication.\n