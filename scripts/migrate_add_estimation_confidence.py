#!/usr/bin/env python3
"""
Migration script to add estimation_confidence column to answers table.
Run this script to update the database schema.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings


def migrate():
    """Add estimation_confidence column to answers table."""

    # Extract database path from database_url
    db_path = settings.database_url.replace("sqlite:///", "")

    print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(answers)")
        columns = [row[1] for row in cursor.fetchall()]

        if "estimation_confidence" in columns:
            print("✓ Column 'estimation_confidence' already exists in answers table")
            return

        # Add the column
        print("Adding 'estimation_confidence' column to answers table...")
        cursor.execute("ALTER TABLE answers ADD COLUMN estimation_confidence TEXT")
        conn.commit()

        print("✓ Migration completed successfully!")
        print("  Column 'estimation_confidence' added to answers table")

    except sqlite3.OperationalError as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
