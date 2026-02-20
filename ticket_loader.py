"""Module for loading tickets from markdown files."""
import os
from pathlib import Path
from config import TICKETS_DIR


def load_tickets_from_folder(folder_name: str) -> list:
    """
    Load all markdown ticket files from a specific folder.
    
    Args:
        folder_name: Name of the folder within tickets/ directory
        
    Returns:
        List of tuples (ticket_name, file_path)
    """
    folder_path = Path(TICKETS_DIR) / folder_name
    
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder '{folder_name}' not found in tickets directory")
    
    if not folder_path.is_dir():
        raise NotADirectoryError(f"'{folder_name}' is not a directory")
    
    tickets = []
    for file in folder_path.glob("*.md"):
        # Use filename without extension as ticket name
        ticket_name = file.stem
        tickets.append({
            "name": ticket_name,
            "path": str(file),
            "folder": folder_name
        })
    
    return tickets


def get_available_folders() -> list:
    """Get a list of all available ticket folders."""
    tickets_path = Path(TICKETS_DIR)
    
    if not tickets_path.exists():
        return []
    
    folders = [d.name for d in tickets_path.iterdir() if d.is_dir()]
    return sorted(folders)
