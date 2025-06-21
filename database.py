import logging
import os
import sqlite3
from datetime import datetime, timezone

from config import AppSettings

logger = logging.getLogger(__name__)


def setup_database() -> None:
    """Initialize the database and table if they don't already exist."""
    db_file = os.environ.get(AppSettings.DB_FILE.value, "ssa.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    # The 'hash' column is the PRIMARY KEY, which automatically creates an
    # efficient index for fast lookups and ensures uniqueness.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_pdfs (
            hash TEXT PRIMARY KEY,
            source_url TEXT NOT NULL,
            first_seen_utc TIMESTAMP NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def hash_exists(pdf_hash: str) -> bool:
    """Check if a hash already exists in the SQLite database."""
    conn = sqlite3.connect(AppSettings.DB_FILE.value)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_pdfs WHERE hash = ?", (pdf_hash,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def add_hash(pdf_hash: str, pdf_url: str) -> None:
    """Add a new PDF hash and its metadata to the SQLite database."""
    conn = sqlite3.connect(AppSettings.DB_FILE.value)
    cursor = conn.cursor()
    timestamp = datetime.now(tz=timezone.utc)
    cursor.execute(
        "INSERT OR IGNORE INTO seen_pdfs (hash, source_url, first_seen_utc) VALUES (?, ?, ?)",
        (pdf_hash, pdf_url, timestamp),
    )
    conn.commit()
    conn.close()
