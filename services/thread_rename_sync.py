"""Safe Discord thread renaming, archive-preserving updates, and title reconciliation."""
from __future__ import annotations

import asyncio
import logging
import re
import time

import discord

logger = logging.getLogger(__name__)

_STATUS_LABELS = {
    "OPEN": "[OPEN]", "CLAIMED": "[CLAIMED]", "PENDING-REVIEW": "[Pending-Review]",
    "REVIEWED": "[Reviewed]", "CLOSED": "[CLOSED]",
}
_NON_ACTOR_TAGS = {"OPEN", "CLAIMED", "PENDING-REVIEW", "REVIEWED", "CLOSED", "CRITICAL", "PRIORITY", "HIGH", "MEDIUM", "LOW"}
_SYSTEM_ACTORS = {"capstoneflow", "discord", "system"}
_FIRST_TAG_RE = re.compile(r"^\[([^\]]+)\]")
_TWO_TAGS_RE = re.compile(r"^\[([^\]]+)\]\s*\[([^\]]+)\]")

_PENDING_RENAMES: dict[int, dict] = {}
_RENAME_COOLDOWN_UNTIL: dict[int, float] = {}
_VERIFIED_THREAD_STATUS: dict[int, str] = {}
_UNREACHABLE_THREADS: set[int] = set()


def clear_rename_sync_state() -> None:
    """Clear in-memory pending renames, cooldowns, and verified thread cache."""
    _PENDING_RENAMES.clear()
    _RENAME_COOLDOWN_UNTIL.clear()
    _VERIFIED_THREAD_STATUS.clear()
    _UNREACHABLE_THREADS.clear()


def strip_leading_bracket_prefixes(title: str) -> str:
    """Strip all leading [STATUS], [PRIORITY], or [actor] bracket tags from a title."""
    cleaned = (title or "").strip()
    while cleaned.startswith("[") and "]" in cleaned:
        cleaned = cleaned.split("]", 1)[1].strip()
    return cleaned or (title or "").strip()


def extract_existing_actor_tag(thread_name: str | None) -> str | None:
    """Extract existing [actor] tag from a thread title like '[Reviewed] [Kesh] CAP-03'."""
    match = _TWO_TAGS_RE.match((thread_name or "").strip())
    if not match:
        return None
    second = match.group(2).strip()
    return None if (not second or second.upper() in _NON_ACTOR_TAGS) else second


def format_status_thread_name(status: str, ticket_name: str, actor: str | None = None) -> str:
    """Build a canonical 100-char-bounded Discord thread title for a ticket status."""
    norm_status = (status or "OPEN").strip().upper()
    prefix = _STATUS_LABELS.get(norm_status, f"[{norm_status}]")
    clean_title = strip_leading_bracket_prefixes(ticket_name)
    clean_actor = (actor or "").strip()
    if norm_status == "OPEN" or not clean_actor or clean_actor.lower() in _SYSTEM_ACTORS:
        return f"{prefix} {clean_title}"[:100]
    return f"{prefix} [{clean_actor}] {clean_title}"[:100]


def expected_thread_name_for_record(row: dict, current_thread_name: str | None = None) -> str:
    """Derive the expected Discord thread title from a database thread record."""
    status = str(row.get("status") or "OPEN").strip().upper()
    ticket_name = str(row.get("ticket_name") or current_thread_name or "Ticket").strip()
    fallback_actor = extract_existing_actor_tag(current_thread_name)
    actor_by_status = {
        "OPEN": None,
        "CLAIMED": row.get("claimed_by_username") or fallback_actor,
        "PENDING-REVIEW": row.get("resolved_by_username") or row.get("claimed_by_username") or fallback_actor,
        "REVIEWED": row.get("reviewed_by_username") or fallback_actor,
        "CLOSED": row.get("reviewed_by_username") or row.get("resolved_by_username") or row.get("claimed_by_username") or fallback_actor,
    }
    return format_status_thread_name(status, ticket_name, actor_by_status.get(status, fallback_actor))


def thread_needs_status_rename(current_name: str | None, target_status: str) -> bool:
    """Return True if the thread's leading [STATUS] tag does not match target_status."""
    match = _FIRST_TAG_RE.match((current_name or "").strip())
    return not match or match.group(1).strip().upper() != (target_status or "").strip().upper()


def queue_pending_thread_rename(
    thread_id: int, target_name: str, *, archived: bool | None = None, locked: bool | None = None, cooldown_seconds: float = 180.0
) -> None:
    """Queue a throttled thread rename for automatic background retry."""
    tid = int(thread_id)
    _PENDING_RENAMES[tid] = {"target_name": (target_name or "")[:100], "archived": archived, "locked": locked}
    _RENAME_COOLDOWN_UNTIL[tid] = time.monotonic() + max(0.0, float(cooldown_seconds))
    _VERIFIED_THREAD_STATUS.pop(tid, None)


def _record_rename_success(thread_id: int | None) -> None:
    if thread_id is not None:
        _PENDING_RENAMES.pop(thread_id, None)
        _RENAME_COOLDOWN_UNTIL.pop(thread_id, None)


async def _apply_fallback_without_name(thread: discord.Thread, edit_kwargs: dict, thread_id: int | None) -> None:
    fallback = {k: v for k, v in edit_kwargs.items() if k != "name"}
    if not fallback or set(fallback.keys()) == {"reason"}:
        return
    try:
        await asyncio.wait_for(thread.edit(**fallback), timeout=2.5)
    except Exception as exc:
        logger.warning("Could not apply fallback thread properties on %s: %s", thread_id or "unknown", exc)


async def _attempt_thread_edit(
    thread: discord.Thread,
    edit_kwargs: dict,
    *,
    thread_id: int | None,
    target_name: str,
    final_kwargs: dict,
    fallback_source: dict,
) -> bool:
    """Execute thread.edit with timeout/429 handling, pending-rename queueing, and non-name fallback."""
    try:
        await asyncio.wait_for(thread.edit(**edit_kwargs), timeout=2.5)
        return True
    except (asyncio.TimeoutError, TimeoutError):
        logger.warning("Discord thread edit timed out (>2.5s) on thread %s; queued rename for retry.", thread_id or "unknown")
        if "name" in edit_kwargs and thread_id is not None:
            queue_pending_thread_rename(
                thread_id, target_name, archived=final_kwargs.get("archived"), locked=final_kwargs.get("locked")
            )
        if "name" in edit_kwargs:
            await _apply_fallback_without_name(thread, fallback_source, thread_id)
        return False
    except discord.HTTPException as exc:
        logger.warning("Discord API HTTP %s editing thread %s (%s). Proceeding with database update.", exc.status, thread_id or "unknown", exc)
        if "name" in edit_kwargs and thread_id is not None and exc.status in (429, 500, 502, 503, 504):
            queue_pending_thread_rename(
                thread_id, target_name, archived=final_kwargs.get("archived"), locked=final_kwargs.get("locked")
            )
        if "name" in edit_kwargs:
            await _apply_fallback_without_name(thread, fallback_source, thread_id)
        return False
    except Exception as exc:
        logger.warning("Unexpected error editing thread %s: %s", thread_id or "unknown", exc)
        return False


async def safe_edit_thread_name(thread: discord.Thread, new_name: str, **kwargs) -> bool:
    """Safely edit thread name and properties across archive states and 429 rate limits."""
    target_name = (new_name or "")[:100]
    current_name = getattr(thread, "name", None)
    raw_tid = getattr(thread, "id", None)
    thread_id = raw_tid if isinstance(raw_tid, int) else None
    is_archived = getattr(thread, "archived", False) is True

    if current_name == target_name and not kwargs:
        _record_rename_success(thread_id)
        return True

    # Discord rejects renaming an already-archived thread with HTTP 400/50083 unless unarchived first.
    if is_archived and kwargs.get("archived") is True:
        reason = kwargs.get("reason")
        if current_name != target_name:
            unarchive_kw: dict = {"name": target_name, "archived": False}
            if reason:
                unarchive_kw["reason"] = reason
            renamed_ok = await _attempt_thread_edit(
                thread, unarchive_kw, thread_id=thread_id, target_name=target_name,
                final_kwargs=kwargs, fallback_source=kwargs,
            )
            if not renamed_ok:
                return False
        try:
            await asyncio.wait_for(thread.edit(**kwargs), timeout=2.5)
            _record_rename_success(thread_id)
            return True
        except Exception as exc:
            logger.warning("Could not re-archive/lock thread %s after rename: %s", thread_id or "unknown", exc)
            return False

    edit_kwargs = dict(kwargs)
    if current_name != target_name:
        edit_kwargs["name"] = target_name
    if is_archived and not edit_kwargs.get("archived", False):
        edit_kwargs["archived"] = False
    if not edit_kwargs or set(edit_kwargs.keys()) == {"reason"}:
        _record_rename_success(thread_id)
        return True

    ok = await _attempt_thread_edit(
        thread, edit_kwargs, thread_id=thread_id, target_name=target_name,
        final_kwargs=kwargs, fallback_source=edit_kwargs,
    )
    if ok:
        _record_rename_success(thread_id)
    return ok


async def _resolve_thread(bot, tid: int) -> discord.Thread | None:
    channel = bot.get_channel(tid)
    if channel is None:
        try:
            channel = await bot.fetch_channel(tid)
        except (discord.NotFound, discord.Forbidden):
            _UNREACHABLE_THREADS.add(tid)
            _PENDING_RENAMES.pop(tid, None)
            return None
        except Exception as exc:
            logger.debug("Could not fetch thread %s during reconciliation: %s", tid, exc)
            return None
    if not isinstance(channel, discord.Thread):
        return None
    return channel


async def reconcile_stale_thread_titles(
    bot,
    threads_by_status: dict | None = None,
    *,
    force: bool = False,
    max_edits: int = 5,
) -> int:
    """Retry queued renames and fix Discord thread titles whose [STATUS] drifted from DB."""
    now = time.monotonic()
    reconciled = 0
    handled_this_run: set[int] = set()

    for tid, spec in list(_PENDING_RENAMES.items()):
        if reconciled >= max_edits:
            break
        if tid in _UNREACHABLE_THREADS:
            _PENDING_RENAMES.pop(tid, None)
            continue
        if not force and now < _RENAME_COOLDOWN_UNTIL.get(tid, 0.0):
            continue
        thread = await _resolve_thread(bot, tid)
        if thread is None:
            continue
        extra = {k: spec[k] for k in ("archived", "locked") if spec.get(k) is not None}
        if reconciled > 0:
            await asyncio.sleep(0.6)
        if await safe_edit_thread_name(thread, spec["target_name"], **extra):
            reconciled += 1
            handled_this_run.add(tid)

    if not isinstance(threads_by_status, dict):
        return reconciled

    ordered_keys = ["CLOSED", "REVIEWED", "PENDING-REVIEW", "CLAIMED", "OPEN"]
    for key in threads_by_status:
        if key not in ordered_keys:
            ordered_keys.append(key)

    for status_key in ordered_keys:
        for row in threads_by_status.get(status_key) or []:
            if reconciled >= max_edits:
                return reconciled
            tid = row.get("thread_id")
            if not isinstance(tid, int) or tid <= 0 or tid in handled_this_run or tid in _UNREACHABLE_THREADS:
                continue
            status = str(row.get("status") or status_key).strip().upper()
            if not force and now < _RENAME_COOLDOWN_UNTIL.get(tid, 0.0):
                continue
            if not force and _VERIFIED_THREAD_STATUS.get(tid) == status:
                continue

            thread = await _resolve_thread(bot, tid)
            if thread is None:
                continue
            current_name = getattr(thread, "name", None)
            needs_rename = thread_needs_status_rename(current_name, status)
            needs_archive = status == "CLOSED" and (
                getattr(thread, "archived", False) is not True or getattr(thread, "locked", False) is not True
            )
            if not needs_rename and not needs_archive:
                _VERIFIED_THREAD_STATUS[tid] = status
                continue

            target_name = expected_thread_name_for_record(row, current_name) if needs_rename else (current_name or "")
            extra = {"archived": True, "locked": True} if status == "CLOSED" else {}
            if reconciled > 0:
                await asyncio.sleep(0.6)
            if await safe_edit_thread_name(thread, target_name, **extra):
                _VERIFIED_THREAD_STATUS[tid] = status
                reconciled += 1
                handled_this_run.add(tid)

    return reconciled
