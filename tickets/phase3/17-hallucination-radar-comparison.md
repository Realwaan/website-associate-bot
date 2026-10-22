# Hallucination Radar Side-by-Side Comparison

**[PRIORITY]**

## Problem
In enterprise compliance pitches, demonstrating value requires showing the contrast between a naive ungrounded model and our grounded Tree-RAG solution. Auditors need to see plain LLMs hallucinating plausible-sounding falsehoods alongside CITEAM's grounded answers and defense refusals.

## Potentially Related Files
- `app/llm.py` - plain Gemma ungrounded baseline caller
- `src/components` - assistant-ui Comparison structured output card
- `app/main.py` - query endpoint baseline payload

## What to Fix
1. Support an `include_baseline` toggle in the UI header and query payload ("Hallucination Radar").
2. Query Plain Gemma synchronously or in an async thread pool without providing any document context.
3. Render a structured side-by-side Comparison card: Amber/Red border for Plain Gemma Baseline ("⚠️ Raw LLM (Ungrounded)"), Emerald border for CITEAM Grounding Engine ("🛡️ Defense Grounded").
4. Highlight differences in citations and factuality between the two answers.
5. Display an explicit refusal comparison when an out-of-bounds query causes Plain Gemma to make up facts while CITEAM correctly refuses.

## Acceptance Criteria
- Toggling Hallucination Radar displays the ungrounded baseline alongside the RAG response.
- Plain Gemma errors are captured gracefully without failing the primary RAG answer.
- Visual side-by-side contrast makes the benefit of Tree-RAG instantly obvious.
- Verified in unit tests and frontend rendering.
