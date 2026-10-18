# 05-top-k-retrieval.md

## Problem
Answers can only be grounded if the right chunks are found for each question, and we need a score to know when nothing relevant exists.

## Potentially Related Files
- `app/retrieve.py` (new)

## What to Fix
1. Embed the question and compute cosine similarity against the index.
2. Return the top 4 chunks with `score`, `doc`, and `page`.
3. Expose `POST /search` for debugging.

## Acceptance Criteria
- A test question returns relevant chunks in under 1 second.
- Each result includes similarity score and page number.
- Unrelated questions return visibly low scores.
