# 01-phase1-environment-and-model-smoke.md

**[CRITICAL]**

## Problem
The ALMA Future Forge Hackathon requires integrating the official ALMA Gemma 4 LLM server. If the team attempts to build RAG indexing before confirming endpoint connectivity, model names, and authentication from our laptops on venue Wi-Fi, the entire project stalls. Additionally, ONNX weights for local embeddings must be pre-downloaded so network drops cannot halt indexing.

## Potentially Related Files
- `app/config.py` - environment variable loader and defaults
- `app/llm.py` - Gemma 4 API client wrapper with timeout protection
- `app/embeddings.py` - FastEmbed ONNX local model initialization
- `.env.example` - clean template for hackathon deployment

## What to Fix
1. Read `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` from environment variables with sensible local fallbacks.
2. Initialize the OpenAI client in `app/llm.py` with an explicit 8.0-second timeout to avoid hung connections on venue Wi-Fi.
3. Write a standalone smoke test function that sends a single test ping to the Gemma 4 server and returns the model response.
4. Pre-warm and verify local FastEmbed ONNX embedding model weights (`BAAI/bge-small-en-v1.5`) to prevent runtime network downloads.
5. Ensure `.env` is listed in `.gitignore` and `.env.example` is documented for all teammates.

## Acceptance Criteria
- Smoke test script successfully queries the ALMA Gemma 4 endpoint and prints a valid response.
- FastEmbed model runs entirely offline without downloading weights during query execution.
- No secrets or API keys are committed to git history.
- Missing or invalid API key triggers a clear diagnostic message rather than an unhandled traceback.
