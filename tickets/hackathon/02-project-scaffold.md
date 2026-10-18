# 02-project-scaffold.md

**[PRIORITY]**

## Problem
Four people cannot work in parallel without an agreed repo layout and a running skeleton app.

## Potentially Related Files
- `app/main.py` - FastAPI entrypoint (new)
- `app/static/index.html` - single-page UI (new)
- `requirements.txt`, `.gitignore`, `README.md`

## What to Fix
1. Create the repo with the folders `app/`, `data/docs/`, `data/index/`.
2. Add FastAPI with a `/health` route and a static page.
3. Add `.gitignore` covering `.env`, `data/index/`, `__pycache__`.
4. Push so all four teammates can branch from it.

## Acceptance Criteria
- `uvicorn app.main:app` starts and `/health` returns OK.
- Everyone has cloned and run it.
- Folder ownership is agreed: ingestion, retrieval, UI, and pitch each have an owner.
