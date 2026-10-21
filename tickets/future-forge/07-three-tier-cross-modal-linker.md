# Three-Tier Cross-Modal Linker for Text and Visuals

**[CRITICAL]**

## Problem
Standard RAG systems treat text and graphics as disconnected modalities. When a paragraph cites 'Figure 2 shows the SLA penalty curve', vector search retrieves only the prose sentence, leaving the auditor without the supporting chart. Furthermore, matching figure numbers against generic page titles (e.g. 'Visual Element (Page 2)') falsely links 'Figure 2' to every unrelated graphic on page 2 while missing Figure 2 on page 3.

## Potentially Related Files
- app/ast_builder.py - symbol extractor, adjacency resolver, and section association
- tests/test_ast_builder.py - cross-modal link verification tests

## What to Fix
1. Implement Tier-1 Symbol Linking: match exact figure and table references ('Figure 1', 'Table II', 'Exhibit A') directly against visual element captions and numbers rather than page string substrings.
2. Implement Tier-2 Spatial Adjacency Linking: link uncaptioned diagrams to the immediately preceding or succeeding paragraph on the same page.
3. Implement Tier-3 Section Association: associate orphaned visuals with their parent section container.
4. Create bidirectional pointers so paragraph leaf nodes know their visual siblings and visual nodes know citing paragraphs.
5. Return cross-modal links as an array of structured link objects in AST serialization.

## Acceptance Criteria
- Paragraphs citing 'Figure 1' or 'Table 1' cleanly resolve to their corresponding visual sibling.
- No false-positive cross-modal links caused by page number substring confusion.
- AST serialization includes an explicit cross_modal_links list with confidence scores.
- Unit tests verify all 3 linking tiers.
