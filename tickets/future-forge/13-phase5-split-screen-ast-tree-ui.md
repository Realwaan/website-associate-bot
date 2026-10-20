# 13-phase5-split-screen-ast-tree-ui.md

**[PRIORITY]**

## Problem
In hackathon presentations, judges get bored staring at standard chat bubbles. To win the UI and Innovation criteria, we need a visual split-screen interface where the left panel renders an interactive hierarchical tree graph of the document AST, and querying dynamically highlights the path traversed down to the visual leaf.

## Potentially Related Files
- `app/static/index.html` - single-page dashboard and tree visualization UI
- `app/main.py` - AST query endpoint `/api/ast`
- `tests/test_api_endpoints.py` - AST endpoint response tests

## What to Fix
1. Expose `GET /api/ast` returning nodes, edges, materialized paths, and cross-modal links.
2. Build an interactive tree graph in `index.html` rendering Document Root, Sections, and Paragraphs.
3. Add dynamic node coloring: cyan for document root, indigo for sections, gray for paragraphs, and purple for visual crops.
4. Implement dynamic path highlighting: when a query finishes, light up the exact active traversal path in neon emerald.
5. Provide a click handler on tree nodes allowing judges to inspect raw node text and bounding box previews.

## Acceptance Criteria
- Tree graph renders automatically upon document upload or sample load.
- Query execution visually illuminates the traversed tree path from root to retrieved leaves.
- Clicking on a node displays its title, page number, and text payload.
- UI renders smoothly without client-side lag or graph overlapping.
