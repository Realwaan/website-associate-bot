"""Module for loading tickets from markdown files."""
import os
import re
import logging
from pathlib import Path
from config import TICKETS_DIR

logger = logging.getLogger(__name__)

PLANNING_FILES = {'readme.md', 'roadmap.md', 'plan.md', 'pdf_brief.md'}


def resolve_ticket_folder(folder_name, root=None):
    base = Path(root or TICKETS_DIR).resolve()
    path = (base / folder_name).resolve()
    if path == base or not path.is_relative_to(base):
        raise ValueError('Choose a folder inside the tickets directory.')
    if not path.is_dir():
        raise FileNotFoundError(f"Ticket folder '{folder_name}' does not exist")
    return path


def ticket_files(folder_name, root=None):
    folder = resolve_ticket_folder(folder_name, root)
    return [p for p in sorted(folder.glob('*.md'))
            if p.name.lower() not in PLANNING_FILES
            and p.resolve().is_relative_to(folder)]


def validate_ticket(ticket):
    missing = [key for key in ('title', 'problem', 'what_to_fix', 'acceptance_criteria') if not ticket.get(key)]
    if missing:
        raise ValueError(f"{ticket['name']}: missing {', '.join(missing)}")
    from datetime import date
    for field in ('start_date', 'due_date'):
        if ticket.get(field):
            date.fromisoformat(ticket[field])
    if ticket.get('start_date') and ticket.get('due_date') and ticket['start_date'] > ticket['due_date']:
        raise ValueError(f"{ticket['name']}: due date precedes start date")
    return ticket


def parse_ticket_markdown(file_path: str) -> dict:
    """
    Parse a ticket markdown file and extract all sections.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Dictionary containing parsed ticket information
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    ticket = {
        "name": Path(file_path).stem,
        "path": file_path,
        "title": None,
        "priority": None,
        "problem": None,
        "related_files": [],
        "what_to_fix": [],
        "acceptance_criteria": [],
        "raw_content": content
    }
    
    # Extract Title (H1)
    title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if title_match:
        raw_title = title_match.group(1).strip()
        # Strip optional leading [TICKET] or [PRIORITY]/[CRITICAL]/[HIGH]/[MEDIUM]/[LOW] tag in title
        clean_title = re.sub(r'^\[(?:TICKET|PRIORITY|CRITICAL|HIGH|MEDIUM|LOW)\]\s*', '', raw_title, flags=re.IGNORECASE).strip()
        ticket["title"] = clean_title or raw_title
    
    # Extract Priority metadata
    priority_match = re.search(r'\*\*\[(PRIORITY|CRITICAL|HIGH|MEDIUM|LOW)\]\*\*', content, re.IGNORECASE)
    if priority_match:
        ticket["priority"] = priority_match.group(1).upper()
    
    # Extract Problem section
    problem_match = re.search(r'## Problem\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if problem_match:
        ticket["problem"] = problem_match.group(1).strip()
    
    # Extract Potentially Related Files (or Related Files) section
    related_files_match = re.search(r'## (?:Potentially )?Related Files\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if related_files_match:
        related_files_text = related_files_match.group(1)
        file_items = re.findall(r'^[\-\*]\s+(.+?)(?:\n|$)', related_files_text, re.MULTILINE)
        ticket["related_files"] = [item.strip() for item in file_items if item.strip()]
    
    # Extract What to Fix section (numbered list or bullet list fallback)
    what_to_fix_match = re.search(r'## What to Fix\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if what_to_fix_match:
        what_to_fix_text = what_to_fix_match.group(1)
        fix_items = re.findall(r'^\d+\.\s+(.+?)(?:\n|$)', what_to_fix_text, re.MULTILINE)
        if not fix_items:
            fix_items = re.findall(r'^[\-\*]\s+(.+?)(?:\n|$)', what_to_fix_text, re.MULTILINE)
        ticket["what_to_fix"] = [item.strip() for item in fix_items if item.strip()]
    
    # Extract Acceptance Criteria section (bullet list or numbered list)
    acceptance_match = re.search(r'## Acceptance Criteria\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if acceptance_match:
        acceptance_text = acceptance_match.group(1)
        criteria_items = re.findall(r'^[\-\*]\s+(?:\[[ xX]\]\s+)?(.+?)(?:\n|$)', acceptance_text, re.MULTILINE)
        if not criteria_items:
            criteria_items = re.findall(r'^\d+\.\s+(.+?)(?:\n|$)', acceptance_text, re.MULTILINE)
        ticket["acceptance_criteria"] = [item.strip() for item in criteria_items if item.strip()]
    
    for key in ('ticket_id', 'start_date', 'due_date', 'timezone', 'owner_suggestion', 'dependencies', 'scope'):
        label = key.replace('_', ' ')
        match = re.search(r'^\*\*' + label + r':\*\*\s*([^\n]+)', content, re.MULTILINE | re.IGNORECASE)
        ticket[key] = match.group(1).strip() if match else None
    return ticket


# Backward-compatible alias
parse_ticket_file = parse_ticket_markdown


def load_tickets_from_folder(folder_name: str) -> list:
    """
    Load all markdown ticket files from a specific folder with full parsing.
    
    Args:
        folder_name: Name of the folder within tickets/ directory
        
    Returns:
        List of parsed ticket dictionaries
    """
    folder_path = resolve_ticket_folder(folder_name)
    
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder '{folder_name}' not found in tickets directory")
    
    if not folder_path.is_dir():
        raise NotADirectoryError(f"'{folder_name}' is not a directory")
    
    tickets = []
    for file in ticket_files(folder_name):
        try:
            ticket = parse_ticket_markdown(str(file))
            ticket["folder"] = folder_name
            tickets.append(ticket)
        except Exception as e:
            logger.warning(f"Failed to parse {file.stem}: {e}")
            tickets.append({
                "name": file.stem,
                "path": str(file),
                "folder": folder_name,
                "title": file.stem,
                "priority": None,
                "problem": None,
                "related_files": [],
                "what_to_fix": [],
                "acceptance_criteria": [],
                "raw_content": ""
            })
    
    return tickets


def get_available_folders() -> list:
    """Get a list of all available ticket folders."""
    tickets_path = Path(TICKETS_DIR)
    
    if not tickets_path.exists():
        return []
    
    folders = [d.name for d in tickets_path.iterdir() if d.is_dir()]
    return sorted(folders)
