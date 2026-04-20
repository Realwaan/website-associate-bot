import sqlite3
import argparse
import os
import sys

def migrate_table(source_conn, dest_conn, table_name, columns):
    """Generic function to migrate a table from source to destination."""
    source_cursor = source_conn.cursor()
    dest_cursor = dest_conn.cursor()
    
    # Check if table exists in source
    source_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    if not source_cursor.fetchone():
        print(f"  [!] Table '{table_name}' not found in source database. Skipping.")
        return

    print(f"  [*] Migrating table '{table_name}'...")
    
    # Get source columns to ensure they exist
    source_cursor.execute(f"PRAGMA table_info({table_name})")
    source_cols = {row[1] for row in source_cursor.fetchall()}
    
    # Filter columns that exist in both source and requested list
    valid_cols = [col for col in columns if col in source_cols]
    
    if not valid_cols:
        print(f"  [!] No valid columns found for table '{table_name}'. Skipping.")
        return

    placeholders = ", ".join(["?" for _ in valid_cols])
    col_str = ", ".join(valid_cols)
    
    source_cursor.execute(f"SELECT {col_str} FROM {table_name}")
    rows = source_cursor.fetchall()
    
    count = 0
    for row in rows:
        try:
            dest_cursor.execute(f"INSERT OR REPLACE INTO {table_name} ({col_str}) VALUES ({placeholders})", row)
            count += 1
        except sqlite3.Error as e:
            print(f"  [!] Error inserting row into {table_name}: {e}")
            
    dest_conn.commit()
    print(f"  [+] Ported {count}/{len(rows)} rows to '{table_name}'.")

def main():
    parser = argparse.ArgumentParser(description="Migrate data from an old website-associate-bot database to a new one.")
    parser.add_argument("source", help="Path to the source (old) database file")
    parser.add_argument("destination", help="Path to the destination (new) database file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source):
        print(f"Error: Source database '{args.source}' not found.")
        sys.exit(1)
        
    if not os.path.exists(args.destination):
        print(f"Error: Destination database '{args.destination}' not found.")
        print("Please initialize the new database first by running the bot once or calling database.init_db().")
        sys.exit(1)

    print(f"=== Starting Migration from '{args.source}' to '{args.destination}' ===")
    
    source_conn = sqlite3.connect(args.source)
    source_conn.row_factory = sqlite3.Row
    dest_conn = sqlite3.connect(args.destination)
    
    # Tables and their respective columns (based on migrations/001_initial_schema.sql)
    migration_map = {
        "threads": [
            "thread_id", "ticket_name", "folder", "channel_id", "status", 
            "created_at", "created_by", "claimed_by_id", "claimed_by_username",
            "resolved_by_id", "resolved_by_username", "pr_url", 
            "reviewed_by_id", "reviewed_by_username"
        ],
        "user_roles": [
            "user_id", "username", "is_developer", "is_qa", "is_pm", "assigned_at"
        ],
        "leaderboard": [
            "user_id", "username", "dev_resolved_count", "qa_reviewed_count",
            "last_dev_resolved", "last_qa_reviewed"
        ],
        "loaded_tickets": [
            "ticket_filename", "folder", "thread_id", "channel_id", "loaded_at"
        ],
        "settings": [
            "key", "value"
        ]
    }
    
    for table, columns in migration_map.items():
        migrate_table(source_conn, dest_conn, table, columns)
        
    source_conn.close()
    dest_conn.close()
    
    print("\n=== Migration Complete ===")
    print("You can now restart your bot with the new database.")

if __name__ == "__main__":
    main()
