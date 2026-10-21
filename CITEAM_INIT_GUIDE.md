# CITEAM — Clean Repository Initialization & Execution Guide

This guide provides the complete, step-by-step instructions for initializing the brand-new **CITEAM** repository on your laptop with **zero trace** of prior prototype repositories.

---

## 1. Project & Repository Identity

* **Project Name:** CITEAM — Hierarchical Multimodal Tree-RAG Grounding Engine
* **GitHub Repository:** `https://github.com/<YourUsername>/citeam.git`
* **Local Workspace Folder:** `citeam`
* **Primary Stack:** Python 3.11+, FastAPI, LanceDB (Apache Arrow/Rust), FastEmbed (ONNX), PyPDFium2 (C++), Google GenAI / Gemma 4

---

## 2. Step-by-Step Repository Initialization

Run these commands in a terminal on your laptop:

### Step 1: Create Directory and Initialize Clean Git
```bash
# Create project folder
mkdir citeam
cd citeam

# Initialize clean Git repository (no ancestry, no forks)
git init -b main

# Set your hackathon identity
git config user.name "Your Name"
git config user.email "your.email@cit.edu"
```

---

### Step 2: Create `.gitignore` First (Prevents Secret Leaks)
Create `.gitignore` before adding any code or data:

```gitignore
# Virtual Environment
.venv/
venv/
ENV/
env/

# Python Bytecode & Cache
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/

# Secrets & Local Environment
.env
.env.*
!.env.example

# Dynamic Runtime Storage & Caches
data/index/
data/docs/*
!data/docs/sample_enterprise_sop.txt
data/previews/*
!data/previews/.gitkeep
data/crops/*
!data/crops/.gitkeep

# Operating System Files
.DS_Store
Thumbs.db
*.swp
*.swo
.vscode/
.idea/
```

---

### Step 3: Create `.env.example` (Configuration Contract)
Create `.env.example` to document required environment variables:

```ini
# CITEAM Grounding Engine Configuration
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma-4
LLM_API_KEY=local-or-alma-key

# Google GenAI Native API Key (Gemma 4 Native)
GEMINI_API_KEY=your_gemini_api_key_here
GEMMA_MODEL=gemma-4-26b-a4b-it
USE_GOOGLE_GENAI=true
LLM_TIMEOUT_SECONDS=60.0

# Retrieval & Evaluation Hyperparameters
SIMILARITY_THRESHOLD=0.58
TOP_K=4
DEFAULT_EMBED_MODEL=BAAI/bge-small-en-v1.5
```

---

### Step 4: Create Pinned `requirements.txt`
Create `requirements.txt` with battle-tested dependency versions:

```text
fastapi==0.115.0
uvicorn==0.31.0
python-multipart==0.0.12
pypdf==5.1.0
pypdfium2>=4.30.0
Pillow>=10.0.0
fastembed>=0.4.0
numpy>=1.26.0
rank-bm25>=0.2.2
openai>=1.50.0
google-genai>=2.30.1
python-dotenv>=1.0.0
pytest>=8.0.0
lancedb>=0.40.0
pyarrow>=16.0.0
python-docx>=1.1.0
python-pptx>=0.6.23
httpx>=0.27.0
```

---

### Step 5: Create Initial `README.md`
Create a fresh, professional `README.md` introducing CITEAM:

````markdown
# 🛡️ CITEAM
### Hierarchical Multimodal Tree-RAG & Cross-Modal Compliance Verification Copilot
*Powered by **Gemma 4**, In-Process **LanceDB (Apache Arrow/Rust)** & C++ **PDFium***

---

## 📌 Executive Summary
Enterprises waste hundreds of hours cross-referencing vendor contracts, financial disclosures, and operational SOPs. General-purpose LLMs hallucinate clauses and fail audits. Furthermore, standard RAG pipelines suffer from **context severance** (separating figures from the text explaining them) and **caption lossiness** (summarizing complex charts into blurry text).

**CITEAM** solves this with a **Compiler-Grade Hierarchical Multimodal Tree-RAG architecture**:
1. **3-Tier Document AST**: Parses document hierarchy (`Root (H0) → Section (H1/H2) → Paragraph (H3) ↔ Visual (Figure/Table)`) with materialized path prefix lookups (`root/01_scope/02_sla/para_1`).
2. **Collision-Bounded Halo Cropper**: Expands visual bounding boxes with 12% outward margin padding to capture axis units and legends without clipping.
3. **Three-Tier Cross-Modal Linker**: Wires bidirectional sibling pointers between text claims and chart visuals using exact symbols, spatial adjacency, and section containers.
4. **Cross-Modal Contradiction Hunter**: Detects discrepancies between author prose claims (*"Uptime guarantee of 99.9%"*) and linked visual evidence (*"Table 1 shows 98.2% breach"*).
5. **2-Tier Epistemic Humility (CRAG Gatekeeper)**: When chunk confidence falls below threshold ($\tau = 0.50$), CITEAM escalates to Whole-Page Scanning. If evidence is missing, it triggers an explicit defense refusal (`OUT-OF-BOUNDS`) rather than fabricating answers.
6. **Embedded In-Process LanceDB Engine**: Columnar vector storage powered by Rust and Apache Arrow with sub-5ms retrieval and zero external Docker dependencies.

---

## 🚀 Quickstart

```bash
# 1. Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pre-warm local ONNX embeddings
python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# 4. Copy configuration
cp .env.example .env

# 5. Run tests
pytest tests/ -v

# 6. Launch server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
````

---

### Step 6: Initial Commit and Push to GitHub
```bash
# Stage initial project scaffolding
git add .gitignore .env.example requirements.txt README.md
git commit -m "chore: initial project initialization for CITEAM"

# Link to your new GitHub repository
git remote add origin https://github.com/<YourUsername>/citeam.git
git push -u origin main
```

---

## 3. Link the Discord Bot to Track `citeam`

In your `website-associate-bot/.env` (on Render or local laptop):

```ini
GITHUB_REPO=<YourUsername>/citeam
```

This ensures that whenever team members run `/claim`, the bot suggests branches for `citeam`, and `/resolved <pr_url>` tracks pull requests against your new repo.

---

## 4. Ticket-Driven Implementation Workflow

Build the project sprint-by-sprint using the 21 pre-configured tickets:

### Sprint 1: Phase 1 (Tickets 01–07)
Load in Discord: `/load-tickets folder: phase1`
1. `01-environment-model-smoke.md`: Implement `app/config.py`, `app/llm.py`, smoke test.
2. `02-fastapi-service-scaffold.md`: Implement `app/main.py`, static mounts, `GET /health`, `POST /export-report`.
3. `03-pypdfium-document-slicer.md`: Implement `app/ingest.py` (PDF, Word, PPTX, TXT, MD).
4. `04-ast-tree-builder.md`: Implement `app/ast_builder.py` (`DOCUMENT_ROOT`, `SECTION`, `PARAGRAPH`, `VISUAL`).
5. `05-raptor-thematic-ast-summarizer.md`: Section-level extractive summaries in `app/ast_builder.py`.
6. `06-collision-bounded-halo-cropper.md`: 12% halo padding, lossless WebP rasterizer in `app/ast_builder.py`.
7. `07-three-tier-cross-modal-linker.md`: Bidirectional text-to-visual linking in `app/ast_builder.py`.

*Sprint 1 Verification Gate:* Run `pytest tests/test_ast_builder.py tests/test_pipeline.py -v` (All Pass).

---

### Sprint 2: Phase 2 (Tickets 08–14)
Load in Discord: `/load-tickets folder: phase2`
8. `08-lancedb-in-process-storage.md`: In-process LanceDB table with 1:1 leaf embeddings (`app/vector_store.py`).
9. `09-hybrid-rrf-retrieval-engine.md`: Hybrid RRF fusing LanceDB + BM25Okapi (`app/retriever.py`).
10. `10-ast-sibling-hydration.md`: Hydrate retrieved chunks with linked visual crops (`app/main.py`).
11. `11-crag-relevance-gatekeeper.md`: 2-tier CRAG with whole-page escalation (`app/retriever.py`, `app/evaluator.py`).
12. `12-formal-nli-entailment-evaluator.md`: CRAG Composite Grounding: $0.60 \times \text{Dense} + 0.40 \times \text{Lexical}$ (`app/evaluator.py`).
13. `13-cross-modal-contradiction-hunter.md`: Metric-specific tolerances (0.5% SLA vs 2.0% business) + vision verification (`app/discrepancy_scanner.py`).
14. `14-adaptive-document-classifier.md`: 5 domain auditor personas + keyword density (`app/classifier.py`).

*Sprint 2 Verification Gate:* Run `pytest tests/test_vector_store.py tests/test_discrepancy_scanner.py -v` (All Pass).

---

### Sprint 3: Phase 3 (Tickets 15–21)
Load in Discord: `/load-tickets folder: phase3`
15. `15-split-screen-ast-tree-ui.md`: Interactive AST tree modal / Flow Graph element (`app/static/`, `src/Modals.tsx`).
16. `16-proof-drawer-image-modal.md`: Clickable citation pills, Proof Drawer, WebP lightbox (`app/generator.py`).
17. `17-hallucination-radar-comparison.md`: Hallucination Radar comparing Raw Gemma vs CITEAM Grounded.
18. `18-automated-compliance-preflight.md`: 7-point corporate audit with negation/disclaimer filters (`app/audit_scanner.py`).
19. `19-compliance-redline-remediation-engine.md`: Pre-approved contract redline diffs (`diff -u`) and `/export-report`.
20. `20-failover-safety-offline-rehearsal.md`: Real token telemetry (`usage_metadata.total_token_count`) and offline fallback.
21. `21-winning-pitch-deck-storyline.md`: 3-minute pitch deck, benchmark matrix, live stage demo.

*Final Verification Gate:* Run `pytest tests/ -v` (**28/28 tests passing 100% green**).

---

## 5. Summary
By following this initialization guide:
* The repository will have a **100% organic, live git history** with timestamps created during the event.
* The codebase will be **completely free of legacy prototypes, old author signatures, and stageware**.
* Every feature will match the production architecture with **full mathematical and functional verification**.
