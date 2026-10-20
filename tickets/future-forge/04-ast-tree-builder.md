# 04-ast-tree-builder.md

**[CRITICAL]**

## Problem
Standard RAG treats documents as flat bags of chunks, destroying the hierarchical relationship between document chapters, policy sections, paragraphs, and nested clauses. When an LLM retrieves a lonely sentence, it misses the parent section context and legal disclaimer governing that clause.

## Potentially Related Files
- `app/ast_builder.py` - AST node definitions and tree hierarchy builder
- `tests/test_ast_builder.py` - AST structure and parent-child verification tests

## What to Fix
1. Define formal AST node types: `DOCUMENT_ROOT (H0)`, `SECTION (H1/H2)`, `PARAGRAPH (H3)`, and `VISUAL (Figure/Table)`.
2. Construct parent-child links so every paragraph node points back to its governing section header.
3. Compute materialized path strings for every node (e.g., `root/01_scope/02_sla/para_1`) for instant prefix-based subtree retrieval.
4. Provide tree traversal methods: `get_ancestors()`, `get_children()`, and `get_leaves()`.
5. Implement JSON serialization so the complete document tree can be visualized in the frontend UI.

## Acceptance Criteria
- AST parses hierarchical markdown headers into a clean tree structure.
- Every paragraph leaf node has a valid parent pointer and materialized path.
- Subtree lookups execute in under 1 millisecond in memory.
- 100% test coverage for node relationships and serialization.
