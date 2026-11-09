# Capstone ticket corrections and bot fixes

## Corrected capstone bundle

All 18 files retain their original filenames so existing import mappings remain valid. Each now includes a stable CAP ID, ISO start/due dates, Asia/Manila timezone, explicit dependencies, and a suggested owner rather than a false assignment. Problem statements describe the observed OTOG implementation gaps. CAP-12 and CAP-13 remain conditional scope; the final readiness date remains December 8, 2026.

Bill payment no longer has a blocking dependency on the final history integration due November 27 when bill payments are due November 25. History integration is coordinated in parallel. Every referenced dependency exists and has a completion date no later than its dependent ticket. Work can start with interface scaffolding; a dependency is required for final integration, not necessarily for starting the first draft.

Existing implementation steps and acceptance criteria remain in the attached complete Markdown. Discord previews are explicitly labeled and bounded; no criteria are silently treated as the full specification when truncated.

## Refresh the existing Discord tickets

After Render deploys this release:

1. Run `/sync-commands` as an authorized server administrator/PM if the new command is not listed.
2. In the text channel containing the original capstone threads, run `/refresh-tickets folder:otog-capstone`.
3. Verify that it reports 18 updated messages (or the number originally imported). The command edits the original bot messages; it does not create new threads or change claims, scores, or statuses.

If threads have not been created, use `/load-tickets folder:otog-capstone`. Do not clear loaded markers just to update ticket wording. Refresh requires the bot to read thread history and edit its original message; it skips missing/unmatched originals rather than guessing which message to overwrite.

## Implemented fixes

- Clone validation permits only exact HTTPS github.com repository URLs. Credentials are origin-scoped, redirects disabled, no token appears in process arguments, and cloning times out after 120 seconds.
- Both scanner paths redact potential credentials before serializing findings. Ordinary print and error logging no longer automatically trigger the broad debug rule. Findings are still heuristic, not guaranteed defects.
- Ticket folders and files are resolved within the configured ticket root; planning documents are excluded. Imports validate all required fields before creating a thread.
- Command authorization uses current Discord roles in the invoking server. Old global database flags no longer grant command permissions across servers. Role assignments still synchronize to the legacy database for compatibility.
- Ticket transitions lock the row and compare the snapshot checked by the command. Score changes commit with the state change instead of independently. This prevents two claims based on the same stale state from both succeeding.
- Imports reserve a channel-scoped job before thread creation. An uncertain creation never automatically repeats. Such jobs require reconciliation using `/rebuild-db`; if creation definitely failed and no thread exists, an administrator may explicitly reset loaded markers for the specific channel after checking it.
- Migration 008 adds reservations and makes loaded-ticket uniqueness channel-specific. It preserves existing thread records.
- Optional `EXPECTED_DISCORD_BOT_ID=1494338948405923850` makes a token/account mismatch close the gateway with an explicit nonsecret diagnostic.

## Validation and remaining limits

The automated suite runs with dotenv disabled and no production database/token. It covers capstone dates/dependency references, content preservation, refresh without workflow changes, uncertain-import duplicate prevention, origin validation, redaction, current-server authorization, stale transition rejection, and atomic SQL transaction boundaries.

The tests use mocked database connections: a real PostgreSQL concurrency/migration drill and live Discord refresh still require staging/operational verification. Thread-rename retry/outbox, durable uploaded ticket storage, server-specific leaderboards/settings, comprehensive AI evaluation, and enterprise dashboard features remain separate work. This release does not claim to complete every commercial-readiness work package or achieve commercial parity.

The existing local deletion of `.github/workflows/ci.yml` is not included in this release. Migration 008 and application code should deploy together. Do not roll back to code using the old two-column import conflict key without a compatible migration plan.
