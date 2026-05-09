"""Configuration module for the Discord bot."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables. Please set it in .env file.")

# Bot configuration
COMMAND_PREFIX = "/"
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Warning: DATABASE_URL not found in environment variables. Database operations may fail.")
TICKETS_DIR = "tickets"

# Scanner configuration
SCAN_IGNORE_DIRS = {
    "node_modules", ".git", ".next", "dist", "build", "out",
    "__pycache__", ".venv", "venv", ".cache", "coverage",
    ".turbo", ".vercel", ".svelte-kit", "vendor", ".idea",
    ".vscode", "public", "static",
}

SCAN_FILE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".py", ".css", ".scss",
    ".java", ".go", ".rb", ".php", ".svelte", ".vue",
    ".html", ".rs", ".cs",
}

SCAN_LARGE_FILE_THRESHOLD = 300  # lines

# Scanner detector toggles (set to false to disable specific categories)
SCAN_ENABLE_TODO = os.getenv("SCAN_ENABLE_TODO", "true").lower() == "true"
SCAN_ENABLE_DEBUG = os.getenv("SCAN_ENABLE_DEBUG", "true").lower() == "true"
SCAN_ENABLE_EMPTY_CATCH = os.getenv("SCAN_ENABLE_EMPTY_CATCH", "true").lower() == "true"
SCAN_ENABLE_SKIPPED_TEST = os.getenv("SCAN_ENABLE_SKIPPED_TEST", "true").lower() == "true"
SCAN_ENABLE_HARDCODED_SECRET = os.getenv("SCAN_ENABLE_HARDCODED_SECRET", "true").lower() == "true"
SCAN_ENABLE_LARGE_FILE = os.getenv("SCAN_ENABLE_LARGE_FILE", "true").lower() == "true"
