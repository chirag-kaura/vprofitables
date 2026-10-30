"""Central path and SQLite connection policy for local and frozen builds."""
import os
import sqlite3
import sys
from pathlib import Path

_IS_FROZEN = getattr(sys, "frozen", False)
BASE_DIR = os.path.dirname(sys.executable) if _IS_FROZEN else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "market_data_v2.db"))
CONFIG_PATH = os.path.normpath(os.path.join(BASE_DIR, "gann_settings.json"))


def get_db_connection(
    readonly: bool = False,
    timeout: float = 15.0,
    *,
    path: str | None = None,
    cache_size_kib: int = 8192,
) -> sqlite3.Connection:
    """Open a consistently configured SQLite connection.

    Read-only connections use SQLite URI ``mode=ro`` so an absent database is
    never silently created. WAL mode is established once by
    :func:`initialize_database`, not renegotiated for each connection.
    """
    db_path = os.path.abspath(path or DB_PATH)
    if readonly:
        uri = Path(db_path).as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=timeout)
        conn.execute("PRAGMA query_only=ON")
    else:
        conn = sqlite3.connect(db_path, timeout=timeout)
        conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(f"PRAGMA busy_timeout={max(0, int(timeout * 1000))}")
    conn.execute(f"PRAGMA cache_size=-{max(1024, int(cache_size_kib))}")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database(path: str | None = None, timeout: float = 30.0) -> int:
    """Initialize WAL and apply the additive, numbered database migrations."""
    db_path = os.path.abspath(path or DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=timeout)
    try:
        conn.execute(f"PRAGMA busy_timeout={max(0, int(timeout * 1000))}")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        current = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if current < 1:
            conn.execute("""
                INSERT OR IGNORE INTO schema_migrations(version, name)
                VALUES (1, 'baseline_existing_schema')
            """)
            conn.execute("PRAGMA user_version=1")
            current = 1
        if current < 2:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_ingest_runs (
                    run_id TEXT PRIMARY KEY,
                    dataset TEXT NOT NULL,
                    source TEXT NOT NULL,
                    started_at_utc TEXT NOT NULL,
                    completed_at_utc TEXT NOT NULL,
                    observed_date TEXT,
                    rows_written INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ingest_runs_dataset_completed
                ON data_ingest_runs(dataset, completed_at_utc DESC)
            """)
            conn.execute("""
                INSERT OR IGNORE INTO schema_migrations(version, name)
                VALUES (2, 'data_ingest_run_provenance')
            """)
            conn.execute("PRAGMA user_version=2")
            current = 2
        conn.commit()
        return current
    finally:
        conn.close()
