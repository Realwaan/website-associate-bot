"""GitHub repository update helpers for commit and merged PR bulletins."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Awaitable, Callable
from urllib.parse import urlparse

import discord

logger = logging.getLogger(__name__)

LAST_SHA_PREFIX = "last_commit_sha:"
LAST_PR_PREFIX = "last_pr_id:"


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
    """GitHub API GET request without blocking the event loop."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def _fetch():
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
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

    for page in range(1, max_pages + 1):
        data = await github_get(
            f"{api_base}/commits?sha={branch}&per_page={per_page}&page={page}",
            token=token,
        )
        if not isinstance(data, list):
            break
        if not data:
            break

        slice_items, found_cursor = _slice_new_items_by_cursor(data, last_sha, "sha")
        aggregated.extend(slice_items)
        if found_cursor:
            found = True
            break
        if len(data) < per_page:
            break

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
) -> tuple[list[dict], int]:
    """Fetch merged pull requests newer than last_pr_id."""
    prs_data = await github_get(
        f"{api_base}/pulls?state=closed&sort=updated&direction=desc&per_page={per_page}",
        token=token,
    )
    if not isinstance(prs_data, list):
        return [], last_pr_id

    merged_prs: list[dict] = []
    for pr in prs_data:
        if not pr.get("merged_at"):
            continue
        if int(pr.get("number", 0)) <= last_pr_id:
            break
        merged_prs.append(pr)

    newest = merged_prs[0].get("number") if merged_prs else last_pr_id
    return merged_prs, int(newest or last_pr_id)


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
) -> tuple[bool, str, int, int]:
    """Fetch and post repository updates to a channel."""
    if feed_type not in {"both", "merged", "commits"}:
        return False, "Invalid feed type. Use one of: both, merged, commits.", 0, 0

    include_commits = feed_type in {"both", "commits"}
    include_merged = feed_type in {"both", "merged"}

    owner, repo = parse_github_repo(repo_url)
    if not owner:
        return False, "Could not parse repository URL. Use a GitHub URL or owner/repo.", 0, 0

    repo_url_clean = f"https://github.com/{owner}/{repo}"
    api_base = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        configured_max_posts = int(os.getenv("REPO_UPDATES_MAX_POSTS", "50"))
    except ValueError:
        configured_max_posts = 50
    max_posts = max(limit, max(10, configured_max_posts))

    new_commits: list[dict] = []
    if include_commits:
        setting_key = f"{LAST_SHA_PREFIX}{owner}/{repo}/{branch}"
        last_sha = await get_setting(setting_key)
        new_commits, newest_sha = await fetch_new_commits(
            api_base=api_base,
            branch=branch,
            last_sha=last_sha,
            token=github_token,
            first_run_limit=limit,
            max_posts=max_posts,
        )
        if newest_sha:
            await set_setting(setting_key, newest_sha)

    merged_prs: list[dict] = []
    if include_merged:
        pr_setting_key = f"{LAST_PR_PREFIX}{owner}/{repo}"
        last_pr = await get_setting(pr_setting_key)
        try:
            last_pr_int = int(last_pr) if last_pr else 0
        except ValueError:
            last_pr_int = 0

        merged_prs, newest_pr = await fetch_new_merged_prs(
            api_base=api_base,
            last_pr_id=last_pr_int,
            token=github_token,
        )
        if newest_pr > last_pr_int:
            await set_setting(pr_setting_key, str(newest_pr))

    if not new_commits and not merged_prs:
        scope_text = {
            "both": "new commits or merged PRs",
            "commits": "new commits",
            "merged": "merged PRs",
        }[feed_type]
        return True, f"No {scope_text} found on `{branch}`.", 0, 0

    now_utc = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    header_embed = discord.Embed(
        title="Project Repository Bulletin",
        description=(
            f"**Repository:** [{owner}/{repo}]({repo_url_clean})\n"
            f"**Branch:** `{branch}`\n"
            f"**Update Scope:** `{feed_type}`\n\n"
            f"This bulletin summarizes newly detected source-control activity.\n"
            f"Reported by {reported_by} on {now_utc}."
        ),
        color=discord.Color.from_rgb(30, 144, 255),
        url=repo_url_clean,
    )
    header_embed.add_field(name="Repository Link", value=f"[Open Repository]({repo_url_clean})", inline=True)
    header_embed.set_footer(text="Formal Source Control Bulletin")
    await target_channel.send(embed=header_embed)

    for idx, pr in enumerate(merged_prs, start=1):
        pr_url = pr.get("html_url", repo_url_clean)
        pr_num = pr.get("number", "?")
        pr_title = pr.get("title", "(no title)")
        pr_author = pr.get("user", {}).get("login", "unknown")
        pr_body = (pr.get("body") or "").strip()
        merged_at_raw = pr.get("merged_at", "")
        merged_dt = None
        if merged_at_raw:
            try:
                merged_dt = datetime.strptime(merged_at_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        description = f"**{pr_title}**"
        if pr_body:
            truncated = pr_body[:300] + ("…" if len(pr_body) > 300 else "")
            description += f"\n\n{truncated}"

        embed = discord.Embed(
            title=f"Merged Pull Request  #{pr_num}",
            description=description,
            url=pr_url,
            color=discord.Color.from_rgb(64, 130, 109),
            timestamp=merged_dt,
        )
        embed.add_field(name="Author", value=f"`{pr_author}`", inline=True)
        embed.add_field(name="PR Number", value=f"[#{pr_num}]({pr_url})", inline=True)
        embed.add_field(name="View PR", value=f"[Open on GitHub]({pr_url})", inline=True)
        embed.set_footer(text=f"Merged PR {idx} of {len(merged_prs)}")
        await target_channel.send(embed=embed)

    for idx, commit in enumerate(new_commits, start=1):
        sha = commit.get("sha", "")
        short_sha = sha[:7]
        commit_info = commit.get("commit", {})
        subject = commit_info.get("message", "(no message)").split("\n")[0]
        author = commit_info.get("author", {}).get("name", "unknown")
        date_raw = commit_info.get("author", {}).get("date", "")
        commit_url = f"{repo_url_clean}/commit/{sha}"

        commit_dt = None
        if date_raw:
            try:
                commit_dt = datetime.strptime(date_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        is_merge = subject.lower().startswith("merge")
        embed_color = discord.Color.from_rgb(88, 101, 242) if is_merge else discord.Color.from_rgb(87, 242, 135)
        kind_label = "Merge Commit" if is_merge else "Commit"

        embed = discord.Embed(
            title=f"{kind_label}  {short_sha}",
            description=f"**{subject}**",
            url=commit_url,
            color=embed_color,
            timestamp=commit_dt,
        )
        embed.add_field(name="Author", value=f"`{author}`", inline=True)
        embed.add_field(
            name="Date",
            value=commit_dt.strftime("%d %b %Y, %H:%M UTC") if commit_dt else "—",
            inline=True,
        )
        embed.add_field(name="Reference", value=f"[View on GitHub]({commit_url})", inline=True)
        embed.set_footer(text=f"Commit {idx} of {len(new_commits)}")
        await target_channel.send(embed=embed)

    return True, "Posted update bulletin.", len(new_commits), len(merged_prs)
