# Ticket Guidelines

This document explains how to write, format, and scope tickets for projects managed by the Website Associate Bot.

## When to Create a Ticket

Create a ticket when you discover or plan:
- A bug or unexpected behavior
- A missing feature or user-facing capability
- A refactoring need
- A technical debt issue (TODO, dead code, missing tests)

**One ticket per problem.** Each file should address a single, self-contained issue. If your ticket touches unrelated parts of the codebase, split it.

**Do not create tickets for:**
- Questions — ask in the relevant Discord channel first.
- Vague ideas without a clear problem statement — write the problem down first, then create the ticket.
- Work that depends entirely on 3+ other unfinished tickets — those dependencies need to ship first.

---

## Scoping Tickets for MVP

Every ticket should be small enough for one person to finish before submitting for review. When deciding what to include in a ticket, apply these filters:

### Is It MVP?

A feature belongs in the MVP if it meets **all** of these criteria:

1. **Users interact with it directly.** If nobody sees it, it is infrastructure — defer it or fold it into a ticket that has a visible outcome.
2. **It works without other unbuilt features.** If the feature needs three other tickets done first, it is not MVP — those dependencies are.
3. **You can demo it in under 60 seconds.** If the demo needs a five-minute setup explanation, you are building too much at once.
4. **One person can finish it in one sitting.** A ticket that takes a full sprint is a project, not a ticket.

### Identifying the Best Feature to Build Next

When multiple tickets are open and the team needs to pick what to work on:

1. **What is blocking other tickets?** Build that first. Mark it `[PRIORITY]`.
2. **What is the smallest ticket that produces a visible result?** Quick wins build momentum and let QA start reviewing early.
3. **What has the most acceptance criteria already written?** Well-scoped tickets are faster to close. Ambiguous ones stall.

If none of the open tickets feel like the right next step, the problem is usually that the remaining tickets are too large. Split the most promising one into two or three smaller tickets, then pick the smallest piece.

---

## Preventing Scope Creep in Tickets

Scope creep is when a ticket quietly expands to include "while we're at it" work. The ticket format fights this by design, but the writer has to cooperate.

### Rules

1. **The Problem section defines the boundary.** Every item in "What to Fix" must trace back to the problem. If it does not, it belongs in a separate ticket.
2. **Acceptance criteria are the contract.** When a developer runs `/resolved`, QA checks the acceptance criteria — nothing more. Do not add criteria that go beyond the stated problem.
3. **Do not use "and" in ticket titles.** If the title says "Fix navbar and add search and update footer," that is three tickets.
4. **Cap "What to Fix" at 8–10 steps.** If you need more, the ticket is too broad. Split it.
5. **Keep related files to one area of the codebase.** If you are listing files from 3+ unrelated directories, the scope is too wide.
6. **Never mix bug fixes with new features.** A bug fix ticket should restore expected behavior. A feature ticket should add new behavior. Combining them makes QA review unclear.

### Red Flags

Watch for these when writing or reviewing a ticket:

- "What to Fix" has more than 10 steps.
- Steps reference files across 3+ unrelated directories.
- Acceptance criteria include items not mentioned in the Problem section.
- The ticket title contains "and."
- Estimated effort exceeds what one developer can finish before submitting for review.
- The Problem section describes multiple unrelated issues.

If any of these appear, split the ticket.

---

## Ticket Format

All tickets should follow this standard structure:

### 1. Title (H1)

Clear, action-oriented title describing one problem or feature.

```markdown
# Remove SPORTS link from Navbar

# Implement Login/Register Feature

# Add Daily Facebook Updates Banner to Home Page
```

### 2. Metadata (Optional)

For high-priority tickets, add a priority marker directly below the title:

```markdown
**[PRIORITY]**

or

**[CRITICAL]**
```

| Marker | When to Use |
|--------|-------------|
| `**[PRIORITY]**` | This ticket blocks other tickets or is critical for MVP |
| `**[CRITICAL]**` | Production is broken — fix immediately |
| *(none)* | Standard priority |

Only use these when they genuinely apply. If everything is `[PRIORITY]`, nothing is.

### 3. Problem Section (H2)

Explain **why** this ticket exists. Describe:
- What is broken or missing
- Impact on users or development
- Current state vs. desired state

```markdown
## Problem

The navbar currently displays "Sports" and "Teams" links that should be removed
from the public navigation.
```

```markdown
## Problem

Currently, the application has Supabase auth setup but no public login/register UI.
Users cannot create accounts.
```

### 4. Potentially Related Files (H2)

List file paths relevant to this ticket with brief descriptions.

```markdown
## Potentially Related Files

- [components/public/navbar.tsx](../app/components/public/navbar.tsx) — Line 18–20: navLinks array
- [app/(public)/sports/](../app/app/(public)/sports/) — Route page
- [actions/sport.ts](../app/actions/sport.ts) — Server actions
```

Guidelines:
- Use relative paths starting with `../app/` (from the `/tickets/` directory).
- Mention line numbers or sections when it helps.
- Include a brief description of what each file contains.
- Keep the list under 15 files. If you need more, scope the ticket down.

### 5. What to Fix (H2)

Ordered list of concrete implementation steps. Each step should be actionable and independently verifiable.

```markdown
## What to Fix

1. Remove `/sports` and `/teams` from navLinks array in navbar.tsx
2. Verify routes still accessible via direct URL
3. Update mobile menu navigation
4. Test navigation state preservation
```

Keep this list between 3 and 10 items. If it grows beyond 10, split the ticket.

### 6. Acceptance Criteria (H2)

Testable conditions that define "done." QA uses these and only these to verify the work.

```markdown
## Acceptance Criteria

- "Sports" link is not visible in desktop navbar
- "Teams" link is not visible in mobile menu
- Routes accessible via direct URL (no 404)
- All navigation highlights work after change
```

Every criterion should be binary — pass or fail, no judgment calls. Avoid vague criteria like "looks good" or "works properly."

---

## File Naming

```
{area}-{feature}.md
```

Where `{area}` is:
- `client-` — public-facing UI, client components
- `admin-` — admin dashboard
- `server-` — server actions, API routes, backend logic
- `utils-` — utilities, seeds, scripts, infrastructure

Examples:

```
client-navbar-remove-sports-teams.md
client-general-login-register.md
admin-general-pdf-export.md
server-auth-session-expiry.md
utils-seed-script.md
```

Auto-generated tickets from `/scan-project` follow the same convention with category slugs (e.g., `client-remove-debug-statements-components.md`).

---

## Code References

When referencing code in tickets:
- Use markdown links: `[filename.tsx](../app/path/to/filename.tsx)`
- Include line numbers when helpful: `../app/components/navbar.tsx#L18-L20`
- Describe what is in the file instead of dumping code.
- Do not wrap file path links in backticks.

---

## Tips for Writing Good Tickets

### DO

- Focus on **one problem** per ticket.
- Be **specific** about files and line numbers.
- List implementation steps in logical order.
- Write acceptance criteria that are **testable** and **binary**.
- Mention breaking changes or dependencies on other tickets.
- Keep the ticket small enough to finish in one sitting.
- Reference the MVP criteria above when deciding what to include.

### DON'T

- Mix multiple unrelated problems in one ticket.
- Use vague language ("fix stuff", "improve UI", "clean up code").
- Assume technical context — explain the "why."
- Forget acceptance criteria.
- Include full code snippets — link to the file instead.
- Add "while we're at it" items that go beyond the Problem section.
- Mark everything as `[PRIORITY]`.

---

## Auto-Generated Tickets

The `/scan-project` command scans a codebase and creates tickets automatically. These tickets follow the same format but are grouped by:

- **Area** — determined from file paths (client, admin, server, utils)
- **Category** — the type of issue (TODO, debug statements, empty catches, etc.)
- **Directory** — issues in the same directory are grouped together

Each generated ticket is already scoped tightly: one category of issue, in one directory, with concrete acceptance criteria. If a generated ticket still feels too broad, split it before loading with `/load-tickets`.

### Issue Categories Detected

| Category | Severity | What It Catches |
|----------|----------|-----------------|
| TODO/FIXME/HACK | Medium–High | Inline markers for unfinished work |
| Debug statements | Low | `console.log`, `print()`, `debugger` left in production code |
| Empty catch blocks | Medium | Swallowed exceptions (`catch {}`, `except: pass`) |
| Large files | Low | Files exceeding the line-count threshold |
| Skipped tests | Low | `test.skip`, `xit`, `@pytest.mark.skip` |
| Hardcoded secrets | High | API keys, tokens, passwords in source code |

---

## Example Ticket

```markdown
# Implement Community Post Approval System

## Problem

Community posts are currently visible without moderation. Admins have no way to
review or reject inappropriate discussions.

## Potentially Related Files

- [supabase/migrations/20260216100000_add_threads.sql](../app/supabase/migrations/20260216100000_add_threads.sql)
- [actions/thread.ts](../app/actions/thread.ts)
- [components/admin/](../app/components/admin/)

## What to Fix

1. Add `is_approved` boolean to threads table
2. Make new threads default to `is_approved = false`
3. Create approval server actions
4. Build admin moderation panel
5. Filter unapproved from public view

## Acceptance Criteria

- Admin can see pending threads in dashboard
- Unapproved posts hidden from public
- Admin can approve/reject posts
- Notification shows pending count
```

---

## Directory Structure

All tickets live in `/tickets/` at workspace root, organized into subfolders:

```
website-associate-bot/
├── tickets/
│   ├── intramurals2026/
│   │   ├── client-navbar-remove-sports-teams.md
│   │   ├── client-general-login-register.md
│   │   └── ...
│   ├── borneo/
│   ├── my-scan/
│   └── SideQuest/
├── ticketsguideline.md          (this file)
└── ...
```

---

**Last updated:** April 16, 2026
