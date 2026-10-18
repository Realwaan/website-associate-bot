# 01-gemma-api-smoke-test.md

**[PRIORITY]**

## Problem
Relevance (15%) requires using the ALMA Gemma 4 servers. Nothing else can be built until we know the endpoint, model name, and key actually work from our machines on venue Wi-Fi.

## Potentially Related Files
- `app/llm.py` - thin client wrapper (new)
- `.env.example` - placeholder variable names only

## What to Fix
1. Read `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` from `.env` (never hardcode).
2. Write `app/llm.py` with one `chat(messages)` function (OpenAI-compatible call).
3. Run a one-line "say hello" call and confirm a response.
4. Confirm `.env` is gitignored.

## Acceptance Criteria
- A script prints a Gemma response using only the provided API.
- No API key appears in any tracked file or commit.
- Every teammate can run it locally with their own copy of `.env`; the key is not shared outside the team.
