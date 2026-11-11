"""Lossless ticket attachments with bounded Discord previews."""
import io
import re
import discord

_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _format_related_file(item: str) -> str:
    text = (item or "").strip()
    # Convert non-HTTP markdown links like [Label](F:/path) to clean inline code paths
    def _replace_link(match: re.Match) -> str:
        label, target = match.group(1).strip(), match.group(2).strip()
        if target.startswith(("http://", "https://")):
            return match.group(0)
        return f"`{target}` ({label})"

    text = _MD_LINK_RE.sub(_replace_link, text)
    if "`" not in text:
        text = f"`{text}`"
    return f"📄 {text}"


def ticket_embed(ticket, folder):
    embed = discord.Embed(title=('Ticket: ' + ticket['title'])[:256],
                          description=(ticket.get('problem') or '')[:1200], color=0x38bdf8)
    for label, key in [('Priority', 'priority'), ('Start date', 'start_date'), ('Due date', 'due_date'),
                       ('Timezone', 'timezone'), ('Suggested owner (not assigned)', 'owner_suggestion'),
                       ('Dependencies', 'dependencies'), ('Scope', 'scope')]:
        if ticket.get(key):
            embed.add_field(name=label, value=str(ticket[key])[:300], inline=False)
    embed.add_field(name='Folder', value=folder[:100], inline=False)
    for label, key in [('What to Fix', 'what_to_fix'), ('Acceptance Criteria', 'acceptance_criteria')]:
        value = '\n'.join('- ' + item for item in ticket.get(key, []))
        if value:
            embed.add_field(name=label, value=value[:800], inline=False)
    related_items = ticket.get('related_files') or []
    if related_items:
        related_value = '\n'.join(_format_related_file(item) for item in related_items)
        embed.add_field(name='📁 Related Files', value=related_value[:800], inline=False)
    embed.set_footer(text='Preview only. Attached Markdown contains the complete scope and criteria. Use /claim to take ownership.')
    return embed


def ticket_attachment(ticket):
    return discord.File(io.BytesIO(ticket['raw_content'].encode('utf-8')), filename=ticket['name'] + '.md')
