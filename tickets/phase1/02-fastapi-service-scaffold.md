# 02-fastapi-service-scaffold.md

**[PRIORITY]**

## Problem
The team needs a unified, non-blocking asynchronous FastAPI service skeleton that manages document uploads, in-memory vault state, static asset mounts for rendered PDF crops, and health diagnostics. Without a clear endpoint structure, frontend and backend development cannot proceed concurrently.

## Potentially Related Files
- `app/main.py` - FastAPI application entrypoint and route definitions
- `app/config.py` - directory paths for static storage, crops, and previews
- `tests/test_api_endpoints.py` - API route verification tests

## What to Fix
1. Scaffold directories for `data/previews`, `data/crops`, `data/index`, and `data/docs` automatically at startup.
2. Mount `/static` to serve pre-rendered page previews and visual crops to the UI.
3. Implement `GET /health` returning API status, model configuration, and system timestamp.
4. Implement in-memory multi-document state structures (`DOCUMENT_VAULT` and `DOCUMENT_ASTS`).
5. Ensure all routes use non-blocking patterns so heavy operations do not starve FastAPI's event loop.

## Acceptance Criteria
- `GET /health` returns HTTP 200 with `{ "status": "ok", "app": "AuditGuard RAG" }`.
- Static directories are created automatically without manual folder creation steps.
- Unit tests pass for base API scaffolding.
- Server starts cleanly under Uvicorn without port binding errors.
