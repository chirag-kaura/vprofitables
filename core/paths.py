# core/paths.py
"""
paths.py — Centralized directory and database path resolver
Resolves BASE_DIR, DB_PATH, and CONFIG_PATH correctly in both:
  1. Development mode (running as normal python scripts)
  2. Production mode (running as packaged Windows executables)
"""
import os
import sys

_IS_FROZEN = getattr(sys, 'frozen', False)
if _IS_FROZEN:
    # Packaged exe mode: resolve to the folder containing the executable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Development mode: resolve to the project root directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Single sources of truth for database and configuration files
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "market_data_v2.db"))
CONFIG_PATH = os.path.normpath(os.path.join(BASE_DIR, "gann_settings.json"))

import sqlite3

def get_db_connection(readonly: bool = False, timeout: float = 15.0) -> sqlite3.Connection:
    """
    Factory for robust SQLite database connections.
    If readonly=True, applies PRAGMA query_only=ON to prevent accidental write operations
    while allowing full non-blocking concurrent reads under WAL mode without schema locks.
    """
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)};")
    if readonly:
        conn.execute("PRAGMA query_only = ON;")
    else:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    return conn
