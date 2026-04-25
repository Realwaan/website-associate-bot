# Claim to Branch Workflow Guide

This guide explains what developers should do immediately after claiming a ticket thread.

## Goal

Keep work traceable by mapping each claimed ticket to one dedicated Git branch.

## Standard Flow

1. Open the ticket thread.
2. Run `/claim` inside the thread.
3. The bot replies with:
   - Suggested branch name (for example: `issue/client-auth-login-success-message`)
   - Checkout command
   - Push command
4. In your local project, create the branch:

```bash
git checkout -b issue/<ticket-slug>
```

5. Push the branch upstream:

```bash
git push -u origin issue/<ticket-slug>
```

6. Do the work, commit normally, and open a PR.
7. Back in the same ticket thread, submit:

```text
/resolved <pr_url>
```

## Branch Naming Convention

Use this format:

```text
issue/<short-ticket-slug>
```

Examples:

- `issue/client-community-reporting`
- `issue/admin-general-pdf-export`
- `issue/utils-warning-system-rbac-audit`

Rules:

- Lowercase only
- Use hyphens instead of spaces
- Keep it short and descriptive
- One ticket should map to one branch

## Why This Helps

- Easier PR review and QA tracking
- Cleaner ticket history
- Less context switching and branch confusion
- Better rollback and audit trail

## If Branch Already Exists

If your branch name is already taken locally or remotely, append a short suffix:

- `issue/client-community-reporting-v2`
- `issue/client-community-reporting-keshie`

Then continue with the same claim thread and submit your PR link via `/resolved`.
