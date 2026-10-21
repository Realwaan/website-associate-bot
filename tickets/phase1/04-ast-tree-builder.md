# Construct Hierarchical Document AST and Synchronize Chunks

**[CRITICAL]**

## Problem
Standard RAG treats documents as flat bags of chunks, destroying the hierarchical relationship between document chapters, policy sections, paragraphs, and nested clauses. When an LLM retrieves a lonely sentence, it misses the parent section context and legal disclaimer governing that clause. Furthermore, decoupling sentence chunk indices from AST paragraph nodes causes retrieved passages to point to wrong tree nodes.

## Potentially Related Files
- app/ast_builder.py - AST node definitions and tree hierarchy builder
- app/ingest.py - chunk generation and AST node identifier synchronization
- tests/test_ast_builder.py - AST structure and parent-child verification tests

## What to Fix
1. Define formal AST node types: DOCUMENT_ROOT (H0), SECTION (H1/H2), PARAGRAPH (H3), and VISUAL (Figure/Table).
2. Construct parent-child links so every paragraph node points back to its governing section header.
3. Compute materialized path strings for every node (e.g., 
oot/01_scope/02_sla/para_1) for prefix-based subtree retrieval.
4. Synchronize chunk indexing with AST paragraph nodes so every retrieved chunk's ast_node_id and materialized_path match its true AST leaf node 1:1.
5. Provide tree traversal methods: get_ancestors(), get_children(), and get_leaves().
6. Implement clean JSON serialization (    o_dict()) exposing 
odes as a structured dictionary and cross_modal_links as an array.

## Acceptance Criteria
- AST parses document hierarchy into a clean tree structure with valid parent pointers.
- Every text chunk's ast_node_id accurately matches its corresponding paragraph node in the AST.
- Subtree lookups execute in under 1 millisecond in memory.
- 100% test coverage for node relationships, path matching, and serialization.
