# Failover Safety Offline Rehearsal and Real Token Telemetry

**[CRITICAL]**

## Problem
Venue Wi-Fi during hackathons frequently cuts out or throttles bandwidth right as teams step on stage. In addition, staging fake demo data (e.g. manually injecting synthetic visual nodes with the word 'declined' that don't exist in the file, or pointing to non-existent image thumbnails) destroys credibility if inspected. Fabricating token counts using a static formula also produces inaccurate telemetry.

## Potentially Related Files
- `app/main.py` - sample document loader `/api/sample` and real token reporting
- `app/generator.py` - native token telemetry extraction from LLM response metadata
- `app/discrepancy_scanner.py` - local deterministic heuristic contradiction detector
- `tests/test_api_endpoints.py` - offline fallback and sample loading tests

## What to Fix
1. Load `sample_enterprise_sop.txt` using the standard multi-format document parser without hardcoding synthetic AST nodes or fake words.
2. Provide verified pre-rendered preview image assets on disk (`sample_enterprise_sop_page_1.webp`) so preview thumbnails load cleanly without broken image icons.
3. Extract real token telemetry from Google GenAI (`response.usage_metadata.total_token_count`) or client usage objects rather than guessing with static formulas.
4. Transparently flag fallback responses (`is_fallback: True`) when operating offline or when LLM API times out.
5. Provide pre-filled question buttons ("Check Uptime SLA", "Audit Wire Transfers", "Detect Contradictions") for 1-click execution on stage.

## Acceptance Criteria
- One-click sample load completes in under 100 milliseconds using standard parsing.
- Real token counts are reported for active queries; refusals and fallbacks reflect true token usage.
- Preview thumbnails load without 404 or broken image errors.
- Full end-to-end demo can be executed entirely offline with Wi-Fi disconnected.
- Unit tests verify sample document loading and telemetry accuracy.
