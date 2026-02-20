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
DATABASE_FILE = "tickets.db"
TICKETS_DIR = "tickets"
