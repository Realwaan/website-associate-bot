# Connect to Gemma Model and Run Smoke Test

**[CRITICAL]**

## Problem
The hackathon deployment requires connecting to the official Gemma 4 LLM server (via native Google GenAI SDK with GEMINI_API_KEY or an OpenAI-compatible endpoint). If the team attempts to build RAG indexing before confirming endpoint connectivity, model names, and authentication, the entire project stalls. Additionally, ONNX weights for local embeddings must be pre-downloaded so network drops cannot halt indexing.

## Potentially Related Files
- app/config.py - environment variable loader, GEMINI_API_KEY, and dynamic model getters
- app/llm.py - Google GenAI and OpenAI-compatible client wrappers with 15s timeout protection
- app/embeddings.py - FastEmbed ONNX local model initialization (BAAI/bge-small-en-v1.5)
- .env.example - clean template for hackathon deployment

## What to Fix
1. Read GEMINI_API_KEY, USE_GOOGLE_GENAI, LLM_BASE_URL, LLM_MODEL, and LLM_API_KEY from environment variables.
2. Support dynamic Gemma model selection (get_gemma_model() and set_gemma_model()) supporting gemma-4-26b-a4b-it and gemma-4-31b-it.
3. Set LLM client timeout to 15.0 seconds with 1 retry to prevent silent timeouts on multi-sentence synthesis while protecting against network hangs.
4. Write a standalone smoke test function that sends a test ping to the Gemma 4 server and returns the verified response.
5. Pre-warm and verify local FastEmbed ONNX embedding model weights (BAAI/bge-small-en-v1.5) to prevent runtime network downloads.
6. Ensure .env is listed in .gitignore and .env.example is documented with required keys.

## Acceptance Criteria
- Smoke test script successfully queries the Gemma 4 endpoint and prints a valid response.
- FastEmbed model runs entirely offline without downloading weights during query execution.
- No secrets or API keys are committed to git history.
- Missing or invalid API key triggers a clear diagnostic message rather than an unhandled traceback.
