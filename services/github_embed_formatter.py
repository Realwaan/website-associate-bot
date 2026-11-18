"""Pure formatting helpers and Discord embed builders for GitHub activity feeds."""
from __future__ import annotations

import re
from datetime import datetime, timezone

import discord

_MACHINE_AUTHOR_RE = re.compile(
    r"(?i)(?:^(?:lab\d+|ws\d+|desktop-[a-z0-9-]+|laptop-[a-z0-9-]+|user|root|ubuntu)$|\bon\s+ws\d+\b)"
)
_CAP_TICKET_RE = re.compile(r"\b(CAP-\d{1,3})\b", re.IGNORECASE)
_PR_MERGE_RE = re.compile(r"(?i)^merge (?:pull request|pr) #(\d+)\b")
_BRANCH_SYNC_RE = re.compile(r"(?i)^merge (?:remote-tracking )?branch\b")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_EPOCH_DT = datetime.min.replace(tzinfo=timezone.utc)


def parse_github_datetime(raw: str | None) -> datetime | None:
    """Parse a GitHub ISO-8601 timestamp string into a UTC-aware datetime."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def format_discord_timestamp(dt: datetime | None, style: str = "t", include_relative: bool = True) -> str:
    """Format a datetime using Discord's client-localized dynamic timestamp syntax."""
    if dt is None:
        return "—"
    aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    unix = int(aware.timestamp())
    return f"<t:{unix}:{style}> (<t:{unix}:R>)" if include_relative else f"<t:{unix}:{style}>"


def is_machine_author_name(name: str | None) -> bool:
    """Return True when git author name looks like a lab/workstation account placeholder."""
    cleaned = (name or "").strip()
    return bool(cleaned and _MACHINE_AUTHOR_RE.search(cleaned))


def format_author_inline(git_name: str | None, github_login: str | None = None, *, compact: bool = False) -> str:
    """Format commit/PR author preferring clickable @GitHub handle over workstation names."""
    name = (git_name or "").strip()
    login = (github_login or "").strip().lstrip("@")
    if login:
        handle_link = f"[@{login}](https://github.com/{login})"
        if compact or not name or name.lower() == login.lower() or is_machine_author_name(name):
            return handle_link
        return f"{name} ({handle_link})"
    return f"`{name or 'unknown'}`"


def extract_linked_tickets_text(
    texts: list[str], ticket_lookup: dict[str, int | str] | None = None
) -> str | None:
    """Extract CAP-XX ticket keys and link them to Discord threads when available."""
    combined = " ".join(t for t in texts if t)
    if not combined:
        return None

    seen: dict[str, int] = {}
    for match in _CAP_TICKET_RE.finditer(combined):
        num = int(match.group(1).split("-", 1)[1])
        canonical = f"CAP-{num:02d}" if num < 100 else f"CAP-{num}"
        seen.setdefault(canonical, num)
    if not seen:
        return None

    lookup = ticket_lookup or {}
    parts = [
        target if isinstance(target, str) else (f"<#{target}> (**{cap}**)" if target else f"`{cap}`")
        for cap, num in sorted(seen.items(), key=lambda item: item[1])
        for target in [lookup.get(cap) or lookup.get(f"CAP-{num}")]
    ]
    joined = ", ".join(parts)
    if len(joined) <= 1000:
        return joined
    kept, total = [], 0
    for part in parts:
        sep = 2 if kept else 0
        if total + sep + len(part) > 980:
            kept.append("…")
            break
        kept.append(part)
        total += sep + len(part)
    return ", ".join(kept)


def classify_commit_subject(subject: str) -> tuple[str, int | None]:
    """Classify commit subject as 'pr_merge', 'branch_sync', or 'normal'."""
    text = (subject or "").strip()
    pr_match = _PR_MERGE_RE.match(text)
    if pr_match:
        return "pr_merge", int(pr_match.group(1))
    if _BRANCH_SYNC_RE.match(text):
        return "branch_sync", None
    return "normal", None


def _truncate_text(text: str, limit: int) -> str:
    single = " ".join((text or "").split())
    return single if len(single) <= limit else single[: max(1, limit - 1)].rstrip() + "…"


def _clean_markdown_snippet(text: str | None, max_len: int) -> str:
    cleaned = _HTML_COMMENT_RE.sub("", text or "")
    cleaned = re.sub(r"\n{3,}", "\n\n", re.sub(r"\r\n?", "\n", cleaned)).strip()
    return cleaned if len(cleaned) <= max_len else cleaned[: max(1, max_len - 1)].rstrip() + "…"


def _resolve_embed_author(
    *, pushed_by_login: str | None, pushed_by_avatar: str | None, commits: list[dict]
) -> tuple[str, str | None, str | None]:
    latest = commits[-1] if commits else {}
    login = (pushed_by_login or latest.get("author_login") or "").strip().lstrip("@") or None
    avatar = pushed_by_avatar or latest.get("author_avatar")
    raw_name = (latest.get("author_name") or "").strip()
    if login:
        if raw_name and raw_name.lower() != login.lower() and not is_machine_author_name(raw_name):
            display = f"{raw_name} (@{login})"
        else:
            display = f"@{login}"
        return display[:256], f"https://github.com/{login}", avatar
    return (raw_name or "GitHub")[:256], None, avatar


def _chunk_commit_lines(lines: list[str], max_items: int = 10, max_chars: int = 3500) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        added = len(line) + (1 if current else 0)
        if current and (len(current) >= max_items or current_len + added > max_chars):
            chunks.append(current)
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append(current)
    return chunks


def build_grouped_push_embeds(
    *, owner: str, repo: str, branch: str, commits: list[dict],
    compare_url: str | None = None, pushed_by_login: str | None = None,
    pushed_by_avatar: str | None = None, posted_pr_numbers: set[int] | None = None,
    ticket_lookup: dict[str, int | str] | None = None,
) -> list[discord.Embed]:
    """Build grouped chronological Discord embeds for commits in a single branch push/sync."""
    if not commits:
        return []

    ordered = sorted(commits, key=lambda c: c.get("dt") or _EPOCH_DT)
    posted_prs = posted_pr_numbers or set()
    substantive, sync_commits = [], []
    for commit in ordered:
        kind, pr_num = classify_commit_subject(commit.get("subject") or "")
        if kind == "pr_merge" and pr_num in posted_prs:
            continue
        (sync_commits if kind == "branch_sync" else substantive).append(commit)
    if not substantive and not sync_commits:
        return []

    is_sync_only = not substantive
    active_list = sync_commits if is_sync_only else substantive
    lines = []
    for commit in active_list:
        sha = str(commit.get("sha") or "")
        url = commit.get("url") or f"https://github.com/{owner}/{repo}/commit/{sha}"
        subj = _truncate_text(commit.get("subject") or "(no message)", 95)
        who = format_author_inline(commit.get("author_name"), commit.get("author_login"), compact=True)
        when = format_discord_timestamp(commit.get("dt"), "t", True)
        lines.append(f"• [`{sha[:7] or 'commit'}`]({url}) {subj if is_sync_only else f'**{subj}**'} — {who} · {when}")

    chunks = _chunk_commit_lines(lines)
    if not is_sync_only and sync_commits and chunks:
        shas = ", ".join(f"`{str(c.get('sha') or '')[:7]}`" for c in sync_commits[:3])
        chunks[-1].append(f"↪ _+{len(sync_commits)} branch sync merge ({shas}{'…' if len(sync_commits) > 3 else ''})_")

    author_display, author_url, author_avatar = _resolve_embed_author(
        pushed_by_login=pushed_by_login, pushed_by_avatar=pushed_by_avatar, commits=active_list
    )
    latest_url = active_list[-1].get("url") or f"https://github.com/{owner}/{repo}"
    latest_dt = next((c.get("dt") for c in reversed(ordered) if c.get("dt") is not None), None)
    color = 0x10B981 if branch in {"main", "master"} else 0x38BDF8
    linked_tickets = extract_linked_tickets_text(
        [branch, *(c.get("subject") or "" for c in active_list), *(c.get("body") or "" for c in active_list)],
        ticket_lookup,
    )

    embeds: list[discord.Embed] = []
    total_chunks, total_count = len(chunks), len(active_list)
    for idx, chunk_lines in enumerate(chunks, start=1):
        base_title = (
            f"🔀 Branch sync on `{branch}`" if is_sync_only
            else (f"🔨 1 new commit to `{branch}`" if total_count == 1 else f"🚀 {total_count} new commits to `{branch}`")
        )
        title = f"{base_title} ({idx}/{total_chunks})" if total_chunks > 1 else base_title
        embed = discord.Embed(
            title=title[:256], description="\n".join(chunk_lines)[:4096],
            url=compare_url or latest_url, color=color, timestamp=latest_dt,
        )
        embed.set_author(name=author_display, url=author_url, icon_url=author_avatar)
        embed.add_field(name="🌿 Branch", value=f"`{branch}`"[:1024], inline=True)
        if linked_tickets:
            embed.add_field(name="🎫 Linked Tickets", value=linked_tickets[:1024], inline=True)
        change_val = f"[Compare Diff]({compare_url})" if compare_url else f"[View on GitHub]({latest_url})"
        embed.add_field(name="🔗 Changes", value=change_val[:1024], inline=True)
        embed.set_footer(text=f"{owner}/{repo} • GitHub Sync")
        embeds.append(embed)
    return embeds


def build_pull_request_embed(
    *, owner: str, repo: str, pr: dict, action: str,
    actor_login: str | None = None, actor_avatar: str | None = None, ticket_lookup: dict[str, int] | None = None,
) -> discord.Embed:
    """Build a dedicated Pull Request lifecycle card (opened, reopened, ready, merged, closed)."""
    pr_num = pr.get("number", "?")
    pr_title = (pr.get("title") or "(no title)").strip()
    pr_url = pr.get("html_url") or f"https://github.com/{owner}/{repo}/pull/{pr_num}"
    head_ref, base_ref = (pr.get("head") or {}).get("ref") or "feature", (pr.get("base") or {}).get("ref") or "main"
    pr_user = pr.get("user") or {}
    pr_author_login, merged_by_login = pr_user.get("login"), (pr.get("merged_by") or {}).get("login")
    action_norm = (action or "opened").lower()
    is_merged = bool(pr.get("merged") or pr.get("merged_at")) and action_norm in {"closed", "merged"}
    if is_merged:
        title, color, ts_raw = f"🟣 Pull Request Merged • #{pr_num}", 0x8B5CF6, pr.get("merged_at") or pr.get("updated_at")
    elif action_norm in {"opened", "reopened", "ready_for_review"}:
        verb = {"opened": "Opened", "reopened": "Reopened", "ready_for_review": "Ready"}[action_norm]
        title, color, ts_raw = f"🟢 Pull Request {verb} • #{pr_num}", 0x22C55E, pr.get("created_at") or pr.get("updated_at")
    else:
        title, color, ts_raw = f"⚪ Pull Request Closed • #{pr_num}", 0x64748B, pr.get("closed_at") or pr.get("updated_at")
    event_dt = parse_github_datetime(ts_raw)
    snippet = _clean_markdown_snippet(pr.get("body"), 240)
    description = f"**{pr_title}**" + (f"\n\n{snippet}" if snippet else "")
    embed = discord.Embed(title=title[:256], description=description[:4096], url=pr_url, color=color, timestamp=event_dt)
    header_login = (actor_login or pr_author_login or "").strip().lstrip("@") or None
    if header_login:
        embed.set_author(name=f"@{header_login}", url=f"https://github.com/{header_login}", icon_url=actor_avatar or pr_user.get("avatar_url"))
    author_val = format_author_inline(None, pr_author_login)
    if is_merged and merged_by_login and merged_by_login != pr_author_login:
        author_val += f"\nMerged by {format_author_inline(None, merged_by_login)}"
    embed.add_field(name="🌿 Route", value=f"`{head_ref}` → `{base_ref}`"[:1024], inline=True)
    embed.add_field(name="👤 Author", value=author_val[:1024], inline=True)
    embed.add_field(name="🕒 Time", value=format_discord_timestamp(event_dt, "f", True), inline=True)
    linked = extract_linked_tickets_text([pr_title, head_ref, pr.get("body") or ""], ticket_lookup)
    if linked:
        embed.add_field(name="🎫 Linked Tickets", value=linked[:1024], inline=True)
    embed.add_field(name="🔗 GitHub", value=f"[Open PR #{pr_num}]({pr_url})", inline=True)
    embed.set_footer(text=f"{owner}/{repo} • Pull Request")
    return embed


def build_pr_review_embed(
    *, owner: str, repo: str, pr: dict, review: dict, ticket_lookup: dict[str, int | str] | None = None
) -> discord.Embed | None:
    """Build a PR review feedback card for approved, changes_requested, or commented reviews."""
    state = str(review.get("state") or "").lower()
    body = _clean_markdown_snippet(review.get("body"), 280)
    if (state == "commented" and not body) or state not in {"approved", "changes_requested", "commented"}:
        return None

    pr_num = pr.get("number", "?")
    pr_title = (pr.get("title") or f"Pull Request #{pr_num}").strip()
    review_url = review.get("html_url") or pr.get("html_url") or f"https://github.com/{owner}/{repo}/pull/{pr_num}"
    reviewer = review.get("user") or {}
    reviewer_login = reviewer.get("login")
    submitted_dt = parse_github_datetime(review.get("submitted_at") or pr.get("updated_at"))
    title, color = {
        "approved": (f"✅ PR Approved • #{pr_num}", 0x10B981),
        "changes_requested": (f"🔧 Changes Requested • #{pr_num}", 0xF59E0B),
        "commented": (f"💬 PR Review Feedback • #{pr_num}", 0x3B82F6),
    }[state]

    description = f"**{pr_title}**"
    if body:
        description += "\n\n" + "\n".join(f"> {line}" if line else ">" for line in body.splitlines())

    embed = discord.Embed(title=title[:256], description=description[:4096], url=review_url, color=color, timestamp=submitted_dt)
    if reviewer_login:
        embed.set_author(name=f"@{reviewer_login}", url=f"https://github.com/{reviewer_login}", icon_url=reviewer.get("avatar_url"))
    embed.add_field(name="👤 Reviewer", value=format_author_inline(None, reviewer_login), inline=True)
    embed.add_field(name="🕒 Time", value=format_discord_timestamp(submitted_dt, "f", True), inline=True)
    linked = extract_linked_tickets_text([pr_title, pr.get("body") or "", review.get("body") or ""], ticket_lookup)
    if linked:
        embed.add_field(name="🎫 Linked Tickets", value=linked[:1024], inline=True)
    embed.add_field(name="🔗 Review", value=f"[View Feedback]({review_url})", inline=True)
    embed.set_footer(text=f"{owner}/{repo} • PR Review")
    return embed
