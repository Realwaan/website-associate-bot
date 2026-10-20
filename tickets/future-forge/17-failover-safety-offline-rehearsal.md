# 17-failover-safety-offline-rehearsal.md

**[CRITICAL]**

## Problem
Venue Wi-Fi during hackathons frequently cuts out or throttles bandwidth right as teams step on stage. If a live demo depends entirely on an active internet connection to show off core capabilities, the presentation can fail catastrophically. The project must have a zero-internet offline fallback mode with pre-baked sample data.

## Potentially Related Files
- `app/main.py` - sample document loader `/api/sample` and offline fallback paths
- `app/discrepancy_scanner.py` - local deterministic heuristic contradiction detector
- `app/static/index.html` - offline indicator badge and quick-demo prefill buttons

## What to Fix
1. Embed the verified `sample_enterprise_sop.txt` document directly in the repository with pre-computed embeddings.
2. Provide a one-click "Load Enterprise SOP" button in the UI that loads, parses, and indexes the AST in under 50ms without internet.
3. Ensure the Discrepancy Scanner falls back to local heuristic detection if the Gemma 4 API is unreachable.
4. Add pre-filled question buttons ("Check Uptime SLA", "Audit Wire Transfers", "Detect Contradictions") for quick 1-click execution on stage.
5. Perform a simulated offline dry-run with Wi-Fi disabled to verify zero-crash execution.

## Acceptance Criteria
- Full end-to-end demo can be executed entirely offline with Wi-Fi disconnected.
- One-click sample load completes in under 100 milliseconds.
- Pre-filled query buttons populate the input and trigger verified answers.
- Discrepancy scanner successfully flags the engineered footnote contradiction offline.
