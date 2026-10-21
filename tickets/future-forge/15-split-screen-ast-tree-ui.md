# Interactive AST Hierarchy Explorer and Assistant-UI Integration

**[PRIORITY]**

## Problem
In document audits, reviewing flat text chunks prevents users from understanding where clauses live in the overall document hierarchy. Users need an interactive tree graph visualizing the 3-Tier Document AST (Root -> Section -> Paragraph <-> Visual). In addition, treating `nodes` as an Array when the backend serializes an Object dictionary throws `TypeError: nodes.filter is not a function`, crashing the AST modal.

## Potentially Related Files
- `src/Modals.tsx` / `app/static/app.js` - AST tree graph renderer and modal
- `app/main.py` - AST query endpoint `/api/ast`
- `tests/test_api_endpoints.py` - AST endpoint response tests

## What to Fix
1. Expose `GET /api/ast` returning nodes dictionary, edges, materialized paths, and cross-modal links.
2. In the frontend modal, safely handle dictionary-based AST payloads using `Object.values(data.nodes || {})` to prevent array filter crashes.
3. Build an interactive tree rendering Document Root, Sections, and Paragraph leaves with color-coded badges.
4. Safely render cross-modal link objects without printing `[object Object]`.
5. Support assistant-ui structured Flow Graph / Tree View element for inline thread navigation.
6. Provide click handlers on tree nodes to inspect raw text and materialized paths.

## Acceptance Criteria
- AST tree graph renders cleanly without runtime JavaScript TypeError crashes.
- Cross-modal links display explicit source and target titles.
- Clicking a tree node displays its materialized path and full text.
- Compatible with both assistant-ui and standalone modal viewers.
