"""GitHub repository update helpers for grouped push, PR, and review cards.

JUSTIFICATION:
This file exceeds the standard 300-line threshold because it contains the complete GitHub
polling (with ETag caching, /events hydration, and Atom fallback), event filtering,
persistent cursor tracking, and grouped Discord card dispatch logic for commits, pull
requests, and reviews. Consolidating this behavior prevents race conditions and
synchronization issues across polling and webhook delivery.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable
from urllib.parse import urlparse

import discord

from services.github_embed_formatter import (
    build_grouped_push_embeds,
    build_pr_review_embed,
    build_pull_request_embed,
    is_machine_author_name,
    parse_github_datetime,
)

logger = logging.getLogger(__name__)

LAST_SHA_PREFIX = "last_commit_sha:"
LAST_PR_PREFIX = "last_pr_id:"
LAST_PR_MERGED_AT_PREFIX = "last_pr_merged_at:"
LAST_EVENT_PREFIX = "last_repo_event_id:"
PROJECT_UPDATE_CHANNEL_NAMES = ("project-updates", "github-updates", "repo-updates")

_ETAG_CACHE: dict[tuple[str, bool], tuple[str, dict | list]] = {}
_RATE_LIMIT_UNTIL: dict[str, float] = {}
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_CAP_KEY_RE = re.compile(r"\b(CAP-\d{1,3})\b", re.IGNORECASE)


def clear_github_etag_cache() -> None:
    """Clear in-memory GitHub ETag and rate-limit cooldown caches."""
    _ETAG_CACHE.clear()
    _RATE_LIMIT_UNTIL.clear()


def find_project_updates_channel(guild: discord.Guild | None) -> discord.TextChannel | None:
    """Find the best matching project updates text channel in a guild."""
    if guild is None:
        return None
    channels = list(getattr(guild, "text_channels", None) or [])
    if not channels:
        return None

    preferred_cat_id: int | None = None
    ticket_ch_raw = (os.getenv("CAPSTONE_TICKET_CHANNEL_ID") or "").strip()
    if ticket_ch_raw.isdigit():
        ticket_ch_id = int(ticket_ch_raw)
        ticket_ch = guild.get_channel(ticket_ch_id) if hasattr(guild, "get_channel") else None
        if ticket_ch is None:
            ticket_ch = next((c for c in channels if getattr(c, "id", None) == ticket_ch_id), None)
        cat_id = getattr(ticket_ch, "category_id", None)
        if isinstance(cat_id, int):
            preferred_cat_id = cat_id

    matches: list[tuple[tuple[int, int, int], discord.TextChannel]] = []
    for idx, ch in enumerate(channels):
        ch_name = str(getattr(ch, "name", "") or "").strip().lower()
        if ch_name not in PROJECT_UPDATE_CHANNEL_NAMES:
            continue
        name_rank = PROJECT_UPDATE_CHANNEL_NAMES.index(ch_name)
        ch_cat_id = getattr(ch, "category_id", None)
        cat_name = str(getattr(getattr(ch, "category", None), "name", "") or "").lower()
        if preferred_cat_id is not None and ch_cat_id == preferred_cat_id:
            cat_rank = 0
        elif "capstone" in cat_name:
            cat_rank = 1
        else:
            cat_rank = 2
        matches.append(((cat_rank, name_rank, idx), ch))

    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def build_cap_ticket_lookup(
    threads_by_status: dict | None,
    guild_id: int | None = None,
) -> dict[str, int | str]:
    """Map canonical CAP-XX ticket keys to Discord thread IDs or jump URLs for closed threads."""
    lookup: dict[str, int | str] = {}
    if not isinstance(threads_by_status, dict):
        return lookup
    for status_name, rows in threads_by_status.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            tid = row.get("thread_id")
            if not tid:
                continue
            match = _CAP_KEY_RE.search(str(row.get("ticket_name") or ""))
            if not match:
                continue
            num = int(match.group(1).split("-", 1)[1])
            canonical = f"CAP-{num:02d}" if num < 100 else f"CAP-{num}"
            status = str(row.get("status") or status_name or "").upper()
            eff_gid = row.get("guild_id") or guild_id
            if status == "CLOSED" and isinstance(eff_gid, int) and eff_gid > 0:
                val: int | str = f"[🔒 **{canonical}**](https://discord.com/channels/{eff_gid}/{int(tid)})"
            else:
                val = int(tid)
            lookup.setdefault(canonical, val)
            lookup.setdefault(f"CAP-{num}", val)
    return lookup


def parse_github_repo(repo_url: str) -> tuple[str, str] | tuple[None, None]:
    """Extract owner/repo from GitHub URL or owner/repo shorthand."""
    cleaned = (repo_url or "").strip().rstrip("/").removesuffix(".git")
    if "/" in cleaned and not cleaned.startswith("http"):
        parts = cleaned.split("/")
        if len(parts) == 2 and all(parts):
            return parts[0], parts[1]

    parsed = urlparse(cleaned)
    if parsed.hostname in ("github.com", "www.github.com"):
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] and path_parts[1]:
            return path_parts[0], path_parts[1]
    return None, None


async def github_get(url: str, token: str | None = None) -> dict | list | None:
    """GitHub API GET request with ETag conditional caching without blocking the event loop."""
    rate_key = "auth" if token else "anon"
    if time.monotonic() < _RATE_LIMIT_UNTIL.get(rate_key, 0.0):
        logger.debug("Skipping GitHub API call while %s rate-limit cooldown is active: %s", rate_key, url)
        return None

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "CapStoneFlow-AssociateBot/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    cache_key = (url, bool(token))
    cached = _ETAG_CACHE.get(cache_key)
    if cached and cached[0]:
        headers["If-None-Match"] = cached[0]

    def _fetch():
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                resp_headers = getattr(resp, "headers", None)
                etag = resp_headers.get("ETag") if hasattr(resp_headers, "get") else None
                if isinstance(etag, str) and etag:
                    if len(_ETAG_CACHE) >= 256:
                        _ETAG_CACHE.pop(next(iter(_ETAG_CACHE)), None)
                    _ETAG_CACHE[cache_key] = (etag, payload)
                return payload
        except urllib.error.HTTPError as exc:
            if exc.code == 304 and cached is not None:
                return cached[1]
            if exc.code in (403, 429):
                hdrs = getattr(exc, "headers", None)
                remaining = hdrs.get("X-RateLimit-Remaining") if hasattr(hdrs, "get") else None
                if remaining == "0" or exc.code == 429:
                    _RATE_LIMIT_UNTIL[rate_key] = time.monotonic() + 60.0
                logger.warning("GitHub API rate/access limit (%s) on %s: %s", exc.code, url, exc)
                return None
            logger.warning("GitHub API HTTP error (%s) on %s: %s", exc.code, url, exc)
            return None
        except Exception as exc:
            logger.warning("GitHub API request failed (%s): %s", url, exc)
            return None

    return await asyncio.to_thread(_fetch)


def _slice_new_items_by_cursor(items: list[dict], cursor_value: str | int | None, field: str) -> tuple[list[dict], bool]:
    """Return items newer than cursor while preserving newest-first order."""
    if cursor_value in (None, "", 0):
        return items, True

    new_items: list[dict] = []
    found_cursor = False
    for item in items:
        if str(item.get(field, "")) == str(cursor_value):
            found_cursor = True
            break
        new_items.append(item)
    return new_items, found_cursor


async def fetch_commits_atom_fallback(
    *,
    owner: str,
    repo: str,
    branch: str,
    last_sha: str | None,
    first_run_limit: int,
) -> tuple[list[dict], str | None]:
    """Fallback to GitHub's public Atom commit feed when REST /commits is rate-limited."""
    encoded_branch = urllib.parse.quote(branch or "main", safe="/")
    atom_url = f"https://github.com/{owner}/{repo}/commits/{encoded_branch}.atom"

    def _fetch_xml() -> str | None:
        req = urllib.request.Request(atom_url, headers={"User-Agent": "CapStoneFlow-AssociateBot/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning("GitHub Atom fallback failed (%s): %s", atom_url, exc)
            return None

    xml_text = await asyncio.to_thread(_fetch_xml)
    if not xml_text:
        return [], last_sha

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Could not parse GitHub Atom feed (%s): %s", atom_url, exc)
        return [], last_sha

    parsed_commits: list[dict] = []
    for entry in root.findall(f"{_ATOM_NS}entry"):
        id_text = (entry.findtext(f"{_ATOM_NS}id") or "").strip()
        sha = id_text.rsplit("/", 1)[-1].strip()
        if not sha:
            continue
        link_el = entry.find(f"{_ATOM_NS}link")
        href = link_el.attrib.get("href", "") if link_el is not None else ""
        title = (entry.findtext(f"{_ATOM_NS}title") or "(no message)").strip()
        updated = (entry.findtext(f"{_ATOM_NS}updated") or "").strip()
        author_el = entry.find(f"{_ATOM_NS}author")
        author_name = (author_el.findtext(f"{_ATOM_NS}name") or "").strip() if author_el is not None else ""
        author_uri = (author_el.findtext(f"{_ATOM_NS}uri") or "").strip() if author_el is not None else ""
        login = None
        if author_uri.startswith("https://github.com/"):
            login = author_uri.rstrip("/").rsplit("/", 1)[-1] or None

        parsed_commits.append(
            {
                "sha": sha,
                "html_url": href or f"https://github.com/{owner}/{repo}/commit/{sha}",
                "author": {"login": login} if login else {},
                "commit": {
                    "message": title,
                    "author": {"name": author_name or login or "unknown", "date": updated},
                },
            }
        )

    if not parsed_commits:
        return [], last_sha
    if not last_sha:
        sliced = parsed_commits[: max(1, min(first_run_limit, 30))]
        return sliced, sliced[0]["sha"]
    sliced, _found = _slice_new_items_by_cursor(parsed_commits, last_sha, "sha")
    if not sliced:
        return [], last_sha
    return sliced, sliced[0]["sha"]


async def fetch_new_commits(
    *,
    api_base: str,
    branch: str,
    last_sha: str | None,
    token: str | None,
    first_run_limit: int,
    max_posts: int = 50,
    per_page: int = 100,
    max_pages: int = 8,
) -> tuple[list[dict], str | None]:
    """Fetch commits newer than last_sha with pagination-safe cursoring."""
    if not last_sha:
        bootstrap = max(1, min(first_run_limit, 30))
        data = await github_get(
            f"{api_base}/commits?sha={branch}&per_page={bootstrap}",
            token=token,
        )
        if not isinstance(data, list):
            return [], None
        newest = data[0].get("sha") if data else None
        return data, newest

    aggregated: list[dict] = []
    found = False
    had_api_response = False

    for page in range(1, max_pages + 1):
        data = await github_get(
            f"{api_base}/commits?sha={branch}&per_page={per_page}&page={page}",
            token=token,
        )
        if not isinstance(data, list):
            break
        had_api_response = True
        if not data:
            break

        slice_items, found_cursor = _slice_new_items_by_cursor(data, last_sha, "sha")
        aggregated.extend(slice_items)
        if found_cursor:
            found = True
            break
        if len(data) < per_page:
            break

    if not had_api_response:
        return [], None

    if not aggregated:
        return [], last_sha

    if len(aggregated) > max_posts:
        aggregated = aggregated[:max_posts]

    newest = aggregated[0].get("sha")
    if not found:
        logger.warning(
            "Commit cursor %s not found on branch %s; posted the latest %s commit(s) and advanced cursor to %s",
            last_sha,
            branch,
            len(aggregated),
            newest,
        )
    return aggregated, newest


async def fetch_new_merged_prs(
    *,
    api_base: str,
    last_pr_id: int,
    token: str | None,
    per_page: int = 50,
    last_merged_at: str | None = None,
) -> tuple[list[dict], int]:
    """Fetch merged pull requests newer than last_merged_at or last_pr_id."""
    prs_data = await github_get(
        f"{api_base}/pulls?state=closed&sort=updated&direction=desc&per_page={per_page}",
        token=token,
    )
    if not isinstance(prs_data, list):
        return [], last_pr_id

    last_merged_dt = parse_github_datetime(last_merged_at) if last_merged_at else None
    merged_prs: list[dict] = []
    for pr in prs_data:
        merged_at_raw = pr.get("merged_at")
        if not merged_at_raw:
            continue
        pr_num = int(pr.get("number", 0) or 0)
        if last_merged_dt is not None:
            merged_dt = parse_github_datetime(merged_at_raw)
            if merged_dt is not None and merged_dt > last_merged_dt:
                merged_prs.append(pr)
        else:
            if pr_num <= last_pr_id:
                break
            merged_prs.append(pr)

    newest = max([last_pr_id, *(int(p.get("number", 0) or 0) for p in merged_prs)])
    return merged_prs, int(newest)


def _normalize_rest_commit(commit: dict, repo_url_clean: str) -> dict:
    sha = str(commit.get("sha") or "")
    commit_info = commit.get("commit") or {}
    msg = commit_info.get("message") or "(no message)"
    subject, _, body = msg.partition("\n")
    author_info = commit_info.get("author") or {}
    gh_author = commit.get("author") or {}
    committer_user = commit.get("committer") or {}
    login = gh_author.get("login")
    if not login:
        c_login = committer_user.get("login")
        if c_login and c_login != "web-flow":
            login = c_login
    dt = parse_github_datetime(author_info.get("date") or (commit_info.get("committer") or {}).get("date"))
    return {
        "sha": sha,
        "subject": subject.strip() or "(no message)",
        "body": body.strip(),
        "author_name": author_info.get("name") or login or "unknown",
        "author_login": login,
        "author_avatar": gh_author.get("avatar_url"),
        "dt": dt,
        "url": commit.get("html_url") or f"{repo_url_clean}/commit/{sha}",
    }


def _normalize_payload_commit(
    commit: dict,
    repo_url_clean: str,
    *,
    fallback_dt: datetime | None = None,
    sender_login: str | None = None,
    sender_avatar: str | None = None,
) -> dict:
    sha = str(commit.get("id") or commit.get("sha") or "")
    msg = commit.get("message") or "(no message)"
    subject, _, body = msg.partition("\n")
    author = commit.get("author") or {}
    author_name = (author.get("name") or "").strip() or "unknown"
    author_login = author.get("username") or (sender_login if is_machine_author_name(author_name) else None)
    dt = parse_github_datetime(commit.get("timestamp")) or fallback_dt
    return {
        "sha": sha,
        "subject": subject.strip() or "(no message)",
        "body": body.strip(),
        "author_name": author_name,
        "author_login": author_login,
        "author_avatar": sender_avatar if author_login and author_login == sender_login else None,
        "dt": dt,
        "url": commit.get("url") or f"{repo_url_clean}/commit/{sha}",
    }


async def _hydrate_push_event_commits(
    *,
    api_base: str,
    repo_url_clean: str,
    ev: dict,
    token: str | None,
) -> tuple[list[dict], str | None]:
    payload = ev.get("payload") or {}
    actor = ev.get("actor") or {}
    actor_login = actor.get("login")
    actor_avatar = actor.get("avatar_url")
    ev_dt = parse_github_datetime(ev.get("created_at"))
    before_sha = str(payload.get("before") or "")
    head_sha = str(payload.get("head") or "")
    has_valid_before = bool(before_sha) and set(before_sha) != {"0"}
    compare_url = (
        f"{repo_url_clean}/compare/{before_sha[:7]}...{head_sha[:7]}"
        if has_valid_before and head_sha
        else None
    )

    if head_sha and has_valid_before:
        compare = await github_get(f"{api_base}/compare/{before_sha}...{head_sha}", token=token)
        if isinstance(compare, dict) and isinstance(compare.get("commits"), list) and compare["commits"]:
            return (
                [_normalize_rest_commit(c, repo_url_clean) for c in compare["commits"]],
                compare.get("html_url") or compare_url,
            )

    raw_commits = payload.get("commits") or []
    if not raw_commits and head_sha:
        size = max(1, min(int(payload.get("size") or 5), 10))
        if size == 1:
            single = await github_get(f"{api_base}/commits/{head_sha}", token=token)
            if isinstance(single, dict) and single.get("sha"):
                return [_normalize_rest_commit(single, repo_url_clean)], compare_url
        branch_commits = await github_get(f"{api_base}/commits?sha={head_sha}&per_page={size}", token=token)
        if isinstance(branch_commits, list) and branch_commits:
            return [_normalize_rest_commit(c, repo_url_clean) for c in reversed(branch_commits)], compare_url

    normalized = [
        _normalize_payload_commit(
            c, repo_url_clean, fallback_dt=ev_dt, sender_login=actor_login, sender_avatar=actor_avatar
        )
        for c in raw_commits
        if c.get("sha") or c.get("id")
    ]
    return normalized, compare_url


async def fetch_new_repo_events(
    *,
    api_base: str,
    repo_url_clean: str,
    last_event_id: str | None,
    token: str | None,
    first_run_limit: int = 10,
    is_background_poll: bool = False,
    has_existing_cursor: bool = False,
) -> tuple[list[dict] | None, str | None]:
    """Fetch and hydrate recent GitHub repository events across all branches and PRs."""
    data = await github_get(f"{api_base}/events?per_page=50", token=token)
    if not isinstance(data, list):
        return None, last_event_id
    if not data:
        return [], last_event_id

    newest_id = str(data[0].get("id") or "") or last_event_id
    if last_event_id:
        raw_events, _ = _slice_new_items_by_cursor(data, last_event_id, "id")
    else:
        limit = max(1, min(first_run_limit, 20))
        if is_background_poll and has_existing_cursor:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
            recent = []
            for ev in data:
                ev_dt = parse_github_datetime(ev.get("created_at"))
                if ev_dt is not None and ev_dt >= cutoff:
                    recent.append(ev)
            raw_events = recent[:limit]
        else:
            raw_events = data[:limit]

    normalized_events: list[dict] = []
    for ev in reversed(raw_events):
        ev_type = ev.get("type")
        payload = ev.get("payload") or {}
        actor = ev.get("actor") or {}
        actor_login = actor.get("login")
        actor_avatar = actor.get("avatar_url")

        if ev_type == "PushEvent":
            ref = str(payload.get("ref") or "")
            if ref and not ref.startswith("refs/heads/"):
                continue
            branch = ref.removeprefix("refs/heads/") or "main"
            commits, compare_url = await _hydrate_push_event_commits(
                api_base=api_base, repo_url_clean=repo_url_clean, ev=ev, token=token
            )
            if not commits:
                continue
            normalized_events.append(
                {
                    "kind": "push",
                    "branch": branch,
                    "commits": commits,
                    "compare_url": compare_url,
                    "actor_login": actor_login,
                    "actor_avatar": actor_avatar,
                }
            )
        elif ev_type == "PullRequestEvent":
            action = str(payload.get("action") or "").lower()
            if action not in {"opened", "closed", "reopened", "ready_for_review"}:
                continue
            pr = dict(payload.get("pull_request") or {})
            pr_num = pr.get("number") or payload.get("number")
            if pr_num and (not pr.get("title") or not pr.get("html_url")):
                hydrated = await github_get(f"{api_base}/pulls/{pr_num}", token=token)
                if isinstance(hydrated, dict):
                    pr = {**pr, **hydrated}
            if not pr_num:
                continue
            normalized_events.append(
                {
                    "kind": "pull_request",
                    "action": action,
                    "pr": pr,
                    "actor_login": actor_login,
                    "actor_avatar": actor_avatar,
                }
            )
        elif ev_type == "PullRequestReviewEvent":
            action = str(payload.get("action") or "").lower()
            if action not in {"created", "submitted"}:
                continue
            pr = dict(payload.get("pull_request") or {})
            review = dict(payload.get("review") or {})
            pr_num = pr.get("number")
            if pr_num and not pr.get("title"):
                hydrated = await github_get(f"{api_base}/pulls/{pr_num}", token=token)
                if isinstance(hydrated, dict):
                    pr = {**pr, **hydrated}
            if not review:
                continue
            normalized_events.append(
                {
                    "kind": "pull_request_review",
                    "pr": pr,
                    "review": review,
                }
            )

    return normalized_events, newest_id


async def _is_new_event(
    mark_event_posted: Callable[[str, int], Awaitable[bool]] | None,
    key: str,
    channel_id: int,
) -> bool:
    if mark_event_posted is None:
        return True
    return await mark_event_posted(key, channel_id)


async def _post_event_stream(
    *,
    target_channel: discord.abc.Messageable,
    owner: str,
    repo: str,
    default_branch: str,
    events: list[dict],
    set_setting: Callable[[str, str], Awaitable[None]],
    mark_event_posted: Callable[[str, int], Awaitable[bool]] | None,
    ticket_lookup: dict[str, int] | None,
) -> tuple[int, int, int]:
    ch_id = int(getattr(target_channel, "id", 0) or 0)
    posted_pr_numbers: set[int] = set()
    for item in events:
        if item["kind"] == "pull_request":
            pr = item["pr"]
            is_merged = bool(pr.get("merged") or pr.get("merged_at")) and item["action"] == "closed"
            if is_merged and pr.get("number") is not None:
                posted_pr_numbers.add(int(pr["number"]))

    posted_commits = 0
    posted_prs = 0
    posted_reviews = 0
    latest_default_sha: str | None = None
    latest_pr_num = 0
    latest_merged_at = ""

    for item in events:
        kind = item["kind"]
        if kind == "pull_request":
            pr = item["pr"]
            pr_num = pr.get("number")
            action = item["action"]
            is_merged = bool(pr.get("merged") or pr.get("merged_at")) and action == "closed"
            dedupe_key = f"pr:{owner}/{repo}:{pr_num}" if is_merged else f"pr_state:{owner}/{repo}:{pr_num}:{action}"
            if not await _is_new_event(mark_event_posted, dedupe_key, ch_id):
                continue
            embed = build_pull_request_embed(
                owner=owner, repo=repo, pr=pr, action=action,
                actor_login=item.get("actor_login"), actor_avatar=item.get("actor_avatar"),
                ticket_lookup=ticket_lookup,
            )
            await target_channel.send(embed=embed)
            posted_prs += 1
            if is_merged:
                latest_pr_num = max(latest_pr_num, int(pr_num or 0))
                merged_str = str(pr.get("merged_at") or "")
                if merged_str > latest_merged_at:
                    latest_merged_at = merged_str
        elif kind == "pull_request_review":
            pr = item["pr"]
            review = item["review"]
            embed = build_pr_review_embed(owner=owner, repo=repo, pr=pr, review=review, ticket_lookup=ticket_lookup)
            if embed is None:
                continue
            review_id = review.get("id") or f"{pr.get('number')}:{review.get('submitted_at') or review.get('state')}"
            if not await _is_new_event(mark_event_posted, f"pr_review:{owner}/{repo}:{review_id}", ch_id):
                continue
            await target_channel.send(embed=embed)
            posted_reviews += 1
        elif kind == "push":
            kept: list[dict] = []
            for commit in item["commits"]:
                sha = commit.get("sha") or ""
                if not sha:
                    continue
                if await _is_new_event(mark_event_posted, f"commit:{owner}/{repo}:{sha}", ch_id):
                    kept.append(commit)
            if not kept:
                continue
            if item["branch"] == default_branch:
                latest_default_sha = kept[-1]["sha"]
            embeds = build_grouped_push_embeds(
                owner=owner, repo=repo, branch=item["branch"], commits=kept,
                compare_url=item.get("compare_url"), pushed_by_login=item.get("actor_login"),
                pushed_by_avatar=item.get("actor_avatar"), posted_pr_numbers=posted_pr_numbers,
                ticket_lookup=ticket_lookup,
            )
            for embed in embeds:
                await target_channel.send(embed=embed)
            if embeds:
                posted_commits += len(kept)

    if latest_default_sha:
        await set_setting(f"{LAST_SHA_PREFIX}{owner}/{repo}/{default_branch}", latest_default_sha)
    if latest_pr_num:
        await set_setting(f"{LAST_PR_PREFIX}{owner}/{repo}", str(latest_pr_num))
    if latest_merged_at:
        await set_setting(f"{LAST_PR_MERGED_AT_PREFIX}{owner}/{repo}", latest_merged_at)
    return posted_commits, posted_prs, posted_reviews


async def post_project_updates(
    *,
    target_channel: discord.abc.Messageable,
    repo_url: str,
    branch: str,
    limit: int,
    feed_type: str,
    reported_by: str,
    github_token: str | None,
    get_setting: Callable[[str], Awaitable[str | None]],
    set_setting: Callable[[str, str], Awaitable[None]],
    mark_event_posted: Callable[[str, int], Awaitable[bool]] | None = None,
    ticket_lookup: dict[str, int] | None = None,
    is_background_poll: bool = False,
) -> tuple[bool, str, int, int]:
    """Fetch and post grouped GitHub repository updates to a Discord channel."""
    if feed_type not in {"all", "both", "merged", "commits", "main_only"}:
        return False, "Invalid feed type. Use one of: all, main_only, both, merged, commits.", 0, 0

    owner, repo = parse_github_repo(repo_url)
    if not owner:
        return False, "Could not parse repository URL. Use a GitHub URL or owner/repo.", 0, 0

    repo_url_clean = f"https://github.com/{owner}/{repo}"
    api_base = f"https://api.github.com/repos/{owner}/{repo}"
    sha_setting_key = f"{LAST_SHA_PREFIX}{owner}/{repo}/{branch}"
    try:
        configured_max_posts = int(os.getenv("REPO_UPDATES_MAX_POSTS", "50"))
    except ValueError:
        configured_max_posts = 50
    max_posts = max(limit, max(10, configured_max_posts))

    if feed_type == "all":
        event_key = f"{LAST_EVENT_PREFIX}{owner}/{repo}"
        last_event_id = await get_setting(event_key)
        existing_sha = await get_setting(sha_setting_key)
        events, newest_event_id = await fetch_new_repo_events(
            api_base=api_base,
            repo_url_clean=repo_url_clean,
            last_event_id=last_event_id,
            token=github_token,
            first_run_limit=limit,
            is_background_poll=is_background_poll,
            has_existing_cursor=bool(existing_sha),
        )
        if events is not None:
            if newest_event_id and newest_event_id != last_event_id:
                await set_setting(event_key, newest_event_id)
            if not events:
                return True, "No new repository activity found.", 0, 0
            c_count, p_count, r_count = await _post_event_stream(
                target_channel=target_channel,
                owner=owner,
                repo=repo,
                default_branch=branch,
                events=events,
                set_setting=set_setting,
                mark_event_posted=mark_event_posted,
                ticket_lookup=ticket_lookup,
            )
            if c_count == 0 and p_count == 0 and r_count == 0:
                return True, "No newly postable events after idempotency filter.", 0, 0
            return True, "Posted grouped repository updates.", c_count, p_count

    include_commits = feed_type in {"all", "both", "commits", "main_only"}
    include_merged = feed_type in {"all", "both", "merged", "main_only"}

    new_commits: list[dict] = []
    if include_commits:
        last_sha = await get_setting(sha_setting_key)
        new_commits, newest_sha = await fetch_new_commits(
            api_base=api_base,
            branch=branch,
            last_sha=last_sha,
            token=github_token,
            first_run_limit=limit,
            max_posts=max_posts,
        )
        if newest_sha is None:
            new_commits, newest_sha = await fetch_commits_atom_fallback(
                owner=owner,
                repo=repo,
                branch=branch,
                last_sha=last_sha,
                first_run_limit=limit,
            )
        if newest_sha and newest_sha != last_sha:
            await set_setting(sha_setting_key, newest_sha)

    merged_prs: list[dict] = []
    if include_merged:
        pr_setting_key = f"{LAST_PR_PREFIX}{owner}/{repo}"
        pr_merged_key = f"{LAST_PR_MERGED_AT_PREFIX}{owner}/{repo}"
        last_pr = await get_setting(pr_setting_key)
        last_merged_at = await get_setting(pr_merged_key)
        try:
            last_pr_int = int(last_pr) if last_pr else 0
        except ValueError:
            last_pr_int = 0

        merged_prs, newest_pr = await fetch_new_merged_prs(
            api_base=api_base,
            last_pr_id=last_pr_int,
            token=github_token,
            last_merged_at=last_merged_at,
        )
        if newest_pr > last_pr_int:
            await set_setting(pr_setting_key, str(newest_pr))
        newest_merged_str = max((str(p.get("merged_at") or "") for p in merged_prs), default="")
        if newest_merged_str and newest_merged_str > (last_merged_at or ""):
            await set_setting(pr_merged_key, newest_merged_str)

    if not new_commits and not merged_prs:
        scope_text = {
            "all": "new repository activity",
            "both": "new commits or merged PRs",
            "main_only": "new commits or merged PRs",
            "commits": "new commits",
            "merged": "merged PRs",
        }[feed_type]
        return True, f"No {scope_text} found on `{branch}`.", 0, 0

    ch_id = int(getattr(target_channel, "id", 0) or 0)
    prepared_prs: list[dict] = []
    for pr in reversed(merged_prs):
        pr_num = pr.get("number", "?")
        if await _is_new_event(mark_event_posted, f"pr:{owner}/{repo}:{pr_num}", ch_id):
            prepared_prs.append(pr)

    prepared_commits: list[dict] = []
    for commit in reversed(new_commits):
        sha = commit.get("sha", "")
        if await _is_new_event(mark_event_posted, f"commit:{owner}/{repo}:{sha}", ch_id):
            prepared_commits.append(commit)

    if not prepared_prs and not prepared_commits:
        return True, "No newly postable events after idempotency filter.", 0, 0

    posted_pr_numbers: set[int] = set()
    posted_pr_count = 0
    for pr in prepared_prs:
        if pr.get("number") is not None:
            posted_pr_numbers.add(int(pr["number"]))
        embed = build_pull_request_embed(
            owner=owner, repo=repo, pr=pr, action="closed", ticket_lookup=ticket_lookup
        )
        await target_channel.send(embed=embed)
        posted_pr_count += 1

    posted_commit_count = 0
    if prepared_commits:
        normalized_commits = [_normalize_rest_commit(c, repo_url_clean) for c in prepared_commits]
        embeds = build_grouped_push_embeds(
            owner=owner,
            repo=repo,
            branch=branch,
            commits=normalized_commits,
            posted_pr_numbers=posted_pr_numbers,
            ticket_lookup=ticket_lookup,
        )
        for embed in embeds:
            await target_channel.send(embed=embed)
        if embeds:
            posted_commit_count = len(normalized_commits)

    return True, "Posted grouped repository updates.", posted_commit_count, posted_pr_count


async def post_push_commits_from_payload(
    *,
    target_channel: discord.abc.Messageable,
    repo_owner: str,
    repo_name: str,
    branch: str,
    commits: list[dict],
    mark_event_posted: Callable[[str, int], Awaitable[bool]] | None = None,
    compare_url: str | None = None,
    pusher_login: str | None = None,
    pusher_avatar: str | None = None,
    ticket_lookup: dict[str, int] | None = None,
) -> int:
    """Post grouped commit updates from a GitHub push webhook payload."""
    if not commits:
        return 0

    repo_url_clean = f"https://github.com/{repo_owner}/{repo_name}"
    ch_id = int(getattr(target_channel, "id", 0) or 0)
    normalized: list[dict] = []
    for commit in commits:
        sha = str(commit.get("id") or commit.get("sha") or "")
        if not sha:
            continue
        if not await _is_new_event(mark_event_posted, f"commit:{repo_owner}/{repo_name}:{sha}", ch_id):
            continue
        normalized.append(
            _normalize_payload_commit(
                commit, repo_url_clean, sender_login=pusher_login, sender_avatar=pusher_avatar
            )
        )

    if not normalized:
        return 0

    embeds = build_grouped_push_embeds(
        owner=repo_owner,
        repo=repo_name,
        branch=branch,
        commits=normalized,
        compare_url=compare_url,
        pushed_by_login=pusher_login,
        pushed_by_avatar=pusher_avatar,
        ticket_lookup=ticket_lookup,
    )
    for embed in embeds:
        await target_channel.send(embed=embed)
    return len(normalized) if embeds else 0


async def post_pull_request_from_payload(
    *,
    target_channel: discord.abc.Messageable,
    repo_owner: str,
    repo_name: str,
    pr: dict,
    action: str,
    sender_login: str | None = None,
    sender_avatar: str | None = None,
    mark_event_posted: Callable[[str, int], Awaitable[bool]] | None = None,
    ticket_lookup: dict[str, int] | None = None,
) -> bool:
    """Post a dedicated Pull Request lifecycle card from a GitHub webhook payload."""
    pr_num = pr.get("number")
    if pr_num is None:
        return False
    ch_id = int(getattr(target_channel, "id", 0) or 0)
    is_merged = bool(pr.get("merged") or pr.get("merged_at")) and action == "closed"
    dedupe_key = (
        f"pr:{repo_owner}/{repo_name}:{pr_num}"
        if is_merged
        else f"pr_state:{repo_owner}/{repo_name}:{pr_num}:{action}"
    )
    if not await _is_new_event(mark_event_posted, dedupe_key, ch_id):
        return False

    embed = build_pull_request_embed(
        owner=repo_owner,
        repo=repo_name,
        pr=pr,
        action=action,
        actor_login=sender_login,
        actor_avatar=sender_avatar,
        ticket_lookup=ticket_lookup,
    )
    await target_channel.send(embed=embed)
    return True


async def post_pr_review_from_payload(
    *,
    target_channel: discord.abc.Messageable,
    repo_owner: str,
    repo_name: str,
    pr: dict,
    review: dict,
    mark_event_posted: Callable[[str, int], Awaitable[bool]] | None = None,
    ticket_lookup: dict[str, int] | None = None,
) -> bool:
    """Post a PR review feedback card from a GitHub pull_request_review webhook payload."""
    embed = build_pr_review_embed(
        owner=repo_owner, repo=repo_name, pr=pr, review=review, ticket_lookup=ticket_lookup
    )
    if embed is None:
        return False

    ch_id = int(getattr(target_channel, "id", 0) or 0)
    review_id = review.get("id") or f"{pr.get('number')}:{review.get('submitted_at') or review.get('state')}"
    if not await _is_new_event(mark_event_posted, f"pr_review:{repo_owner}/{repo_name}:{review_id}", ch_id):
        return False

    await target_channel.send(embed=embed)
    return True
