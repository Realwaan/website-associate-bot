# 10-ast-sibling-hydration.md

**[PRIORITY]**

## Problem
When a user asks a question about a technical specification or financial figure, vector search retrieves only the text paragraph. If that paragraph references a diagram or table, the retriever must automatically pull the corresponding visual crop so both the LLM and the human auditor can inspect the visual evidence.

## Potentially Related Files
- `app/main.py` - query pipeline and AST sibling hydration loop
- `app/vector_store.py` - LanceDB sibling retrieval methods
- `tests/test_vector_store.py` - hydration verification tests

## What to Fix
1. In the query pipeline, look up each retrieved text chunk in the active Document AST.
2. Read the `linked_node_ids` on the paragraph node to identify linked visual elements.
3. Hydrate each retrieved chunk with a `linked_visuals` list containing crop ID, title, image URL, visual type, and page number.
4. Set `has_visual = True` and populate `image_url` on the citation chunk for immediate frontend display.
5. Support materialized path filtering so queries scoped to a specific chapter only search descendants of that path.

## Acceptance Criteria
- Querying for a topic discussed in a paragraph linked to "Figure 1" returns both the text and the WebP image URL.
- Hydration completes in memory in under 1 millisecond.
- Front-end payload includes full visual metadata alongside text excerpts.
- Tests verify that chunks with linked visuals are correctly decorated.\n