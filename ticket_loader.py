"""Module for loading tickets from markdown files."""
import os
import re
from pathlib import Path
from config import TICKETS_DIR


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
        ticket["title"] = title_match.group(1).strip()
    
    # Extract Priority metadata
    priority_match = re.search(r'\*\*\[(PRIORITY|CRITICAL)\]\*\*', content)
    if priority_match:
        ticket["priority"] = priority_match.group(1)
    
    # Extract Problem section
    problem_match = re.search(r'## Problem\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if problem_match:
        ticket["problem"] = problem_match.group(1).strip()
    
    # Extract Potentially Related Files section
    related_files_match = re.search(r'## Potentially Related Files\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if related_files_match:
        related_files_text = related_files_match.group(1)
        # Extract bullet points with file references
        file_items = re.findall(r'- (.*?)(?:\n|$)', related_files_text)
        ticket["related_files"] = [item.strip() for item in file_items if item.strip()]
    
    # Extract What to Fix section (numbered list)
    what_to_fix_match = re.search(r'## What to Fix\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if what_to_fix_match:
        what_to_fix_text = what_to_fix_match.group(1)
        # Extract numbered items
        fix_items = re.findall(r'^\d+\.\s+(.+?)(?:\n|$)', what_to_fix_text, re.MULTILINE)
        ticket["what_to_fix"] = [item.strip() for item in fix_items if item.strip()]
    
    # Extract Acceptance Criteria section (bullet list or narrative)
    acceptance_match = re.search(r'## Acceptance Criteria\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if acceptance_match:
        acceptance_text = acceptance_match.group(1)
        # Extract both bullet points and numbered items
        criteria_items = re.findall(r'^[\-\*]\s+(.+?)(?:\n|$)', acceptance_text, re.MULTILINE)
        if not criteria_items:
            # Try numbered format
            criteria_items = re.findall(r'^\d+\.\s+(.+?)(?:\n|$)', acceptance_text, re.MULTILINE)
        ticket["acceptance_criteria"] = [item.strip() for item in criteria_items if item.strip()]
    
    return ticket


def load_tickets_from_folder(folder_name: str) -> list:
    """
    Load all markdown ticket files from a specific folder with full parsing.
    
    Args:
        folder_name: Name of the folder within tickets/ directory
        
    Returns:
        List of parsed ticket dictionaries
    """
    folder_path = Path(TICKETS_DIR) / folder_name
    
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder '{folder_name}' not found in tickets directory")
    
    if not folder_path.is_dir():
        raise NotADirectoryError(f"'{folder_name}' is not a directory")
    
    tickets = []
    for file in folder_path.glob("*.md"):
        try:
            ticket = parse_ticket_markdown(str(file))
            ticket["folder"] = folder_name
            tickets.append(ticket)
        except Exception as e:
            # Log parsing error but continue with other files
            print(f"Warning: Failed to parse {file.stem}: {e}")
            # Add basic ticket info even if parsing failed
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
