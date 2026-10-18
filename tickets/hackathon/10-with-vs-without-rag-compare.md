# 10-with-vs-without-rag-compare.md

## Problem
Judges need to see why RAG matters. A side-by-side of plain Gemma versus grounded Gemma makes the value obvious in seconds.

## Potentially Related Files
- `app/main.py`, `app/static/app.js`

## What to Fix
1. Add a toggle or second column that asks Gemma the same question with no retrieved context.
2. Label both columns clearly.
3. Pick demo questions where the plain model is wrong or vague.

## Acceptance Criteria
- One click shows both answers for the same question.
- The comparison works within the demo time budget.
- At least 2 prepared questions show a clear difference.
