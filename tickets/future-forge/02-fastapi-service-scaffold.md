# Scaffold FastAPI Service and Health Diagnostics

**[PRIORITY]**

## Problem
The team needs a unified, non-blocking asynchronous FastAPI service skeleton that manages multi-format document uploads, in-memory vault state, static asset mounts for rendered crops and previews, report exports, and health diagnostics. Without a clean endpoint structure and verified database pings, frontend and backend development cannot proceed concurrently.

## Potentially Related Files
- app/main.py - FastAPI application entrypoint, routes, and export endpoints
- app/config.py - directory paths for static storage, crops, and previews
- app/vector_store.py - LanceDB connection health check
- tests/test_api_endpoints.py - API route verification tests

## What to Fix
1. Scaffold directories for data/previews, data/crops, data/index, and data/docs automatically at startup.
2. Mount /static to serve pre-rendered page previews and visual crops to the UI.
3. Implement GET /health dynamically pinging LanceDB via LANCE_STORE.db.list_tables() and checking Google GenAI status rather than returning a hardcoded boolean.
4. Implement in-memory multi-document state structures (DOCUMENT_VAULT and DOCUMENT_ASTS).
5. Implement POST /export-report supporting both Markdown and JSON export formats with proper HTTP headers.
6. Ensure all routes use non-blocking patterns so heavy operations do not starve FastAPI event loop.

## Acceptance Criteria
- GET /health returns HTTP 200 with dynamic lancedb_ready, active document status, and model engine details.
- POST /export-report successfully downloads formatted Markdown and JSON files without 404 errors.
- Static directories are created automatically without manual folder creation steps.
- Unit tests pass for base API scaffolding and health check.
