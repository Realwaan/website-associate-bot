# 06-phase2-three-tier-cross-modal-linker.md

**[CRITICAL]**

## Problem
In complex technical and financial documents, text paragraphs frequently discuss figures or tables located elsewhere on the page or on subsequent pages (context severance). If text and visual streams remain disconnected, retrieving a paragraph leaves the LLM blind to the chart that proves or disproves the claim.

## Potentially Related Files
- `app/ast_builder.py` - cross-modal linker and sibling pointer wiring
- `tests/test_ast_builder.py` - symbol regex matching and fallback linker tests

## What to Fix
1. Implement Tier 1 exact and fuzzy symbol matching using regular expressions (`Figure \d+`, `Table \w+`, `Exhibit [A-Z0-9]+`).
2. Wire bidirectional sibling pointers between the citing paragraph AST node and the referenced visual AST node.
3. Implement Tier 2 spatial adjacency fallback: link unreferenced visuals to immediately adjacent paragraphs on the same page.
4. Implement Tier 3 parent section fallback: associate remaining visuals with the parent section header.
5. Provide helper method `ast.get_cross_modal_links()` returning all wired edges with confidence weights.

## Acceptance Criteria
- Paragraphs with "Figure 1" or "Table II" automatically link directly to their corresponding visual node IDs.
- Sibling link is bidirectional: traversing from text finds the chart, and traversing from chart finds citing text.
- Fallback tiers properly assign links when explicit symbol references are omitted by the author.
- Unit tests verify all three tiers of linking behavior.
