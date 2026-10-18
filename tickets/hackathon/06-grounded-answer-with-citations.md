# 06-grounded-answer-with-citations.md

**[PRIORITY]**

## Problem
This is the core demo (working demo = 35%). Gemma must answer only from retrieved chunks and cite them.

## Potentially Related Files
- `app/answer.py` - prompt building (new)
- `app/llm.py`, `app/retrieve.py`

## What to Fix
1. Build a prompt containing numbered chunks and the instruction to answer only from them, citing `[1]`, `[2]`.
2. Call Gemma through `app/llm.py`.
3. Return `{answer, sources: [{n, doc, page, text}]}` from `POST /ask`.

## Acceptance Criteria
- A question about an uploaded document returns an answer with at least one citation.
- Each citation maps to a real chunk with doc name and page.
- End-to-end latency is acceptable for a live demo (target under 10 seconds).
