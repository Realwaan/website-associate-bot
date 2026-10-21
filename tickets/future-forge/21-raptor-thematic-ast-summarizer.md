# 21-raptor-thematic-ast-summarizer.md

**[PRIORITY]**

## Problem
In hierarchical documents, users frequently ask overarching thematic questions (e.g., "What are the primary operational responsibilities and SLA commitments across this agreement?"). Standard chunk retrieval fetches arbitrary paragraph fragments, missing the overarching section scope. Academic systems like RAPTOR and Psi-RAG solve this by generating abstractive summaries at higher tree levels.

## Potentially Related Files
- `app/ast_builder.py` - Document AST hierarchy and section summarizer
- `app/retriever.py` - hybrid retrieval over section summaries and paragraphs
- `tests/test_ast_builder.py` - AST section summary verification tests

## What to Fix
1. Extend `DocumentAST` in `app/ast_builder.py` so that `SECTION` nodes compile an extractive/thematic summary from their child paragraphs.
2. Store `summary_text` and materialized summary paths (e.g., `root/sec_1/summary`) on Section nodes.
3. Allow the hybrid retriever to match high-level thematic queries against section summaries, returning parent context with direct pointers to all child paragraph leaves.
4. Ensure AST serialization (`to_dict()`) exposes section summaries for split-screen graph rendering.
5. Maintain sub-200ms document ingestion without requiring slow recursive LLM summarization.

## Acceptance Criteria
- Every section node with $\ge 1$ child paragraph automatically contains a clean thematic summary.
- Thematic queries can retrieve section-level scope alongside child paragraph proofs.
- Ingestion speed remains under 200ms for a standard enterprise agreement.
- 100% test coverage for section summaries and AST tree serialization.
