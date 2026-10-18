# 07-refuse-when-not-in-documents.md

## Problem
A grounded system that hallucinates when the answer is missing is not trustworthy. Showing a clean refusal live is a strong differentiator for judges.

## Potentially Related Files
- `app/answer.py`, `app/retrieve.py`

## What to Fix
1. Add a similarity threshold; if the best score is below it, skip the LLM call.
2. Return "I could not find this in the uploaded documents" with the closest sources.
3. Tune the threshold using 5 in-scope and 5 out-of-scope questions.

## Acceptance Criteria
- An out-of-scope question (e.g. "Who won the NBA finals?") is refused.
- In-scope test questions still get answered.
- The refusal is shown clearly in the UI.
