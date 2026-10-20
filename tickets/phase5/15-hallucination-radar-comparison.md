# 15-hallucination-radar-comparison.md

**[PRIORITY]**

## Problem
In hackathon pitches, demonstrating value requires showing the contrast between a naive model and our engineered solution. Judges need to see an ungrounded LLM hallucinating plausible-sounding falsehoods alongside AuditGuard's grounded answer and defense refusal.

## Potentially Related Files
- `app/llm.py` - plain Gemma ungrounded baseline caller
- `app/static/index.html` - side-by-side comparison UI card and toggle
- `app/main.py` - query endpoint baseline payload

## What to Fix
1. Add an `include_baseline` toggle switch in the UI header ("Hallucination Radar").
2. Query Plain Gemma 4 synchronously or in an async thread pool without providing any document context.
3. Render a side-by-side comparison card: Red border for Plain Gemma Baseline ("⚠️ Raw LLM (Ungrounded)"), Emerald border for AuditGuard RAG ("🛡️ Defense Grounded").
4. Highlight differences in citations and factuality between the two answers.
5. Display an explicit refusal comparison when an out-of-bounds query causes Plain Gemma to make up facts while AuditGuard refuses.

## Acceptance Criteria
- Toggling Hallucination Radar displays the ungrounded baseline alongside the RAG response.
- Plain Gemma errors are captured gracefully without failing the primary RAG answer.
- Visual side-by-side contrast makes the benefit of Tree-RAG instantly obvious in under 15 seconds.
- Verified in unit tests and manual browser smoke testing.
