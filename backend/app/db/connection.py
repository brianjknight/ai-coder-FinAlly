"""SQLite connection management, lazy schema init and seeding."""

from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0
DEFAULT_WATCHLIST = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = Path(__file__).with_name("schema.sql")

_lock = threading.Lock()
_db_path: str | None = None  # explicit override set by init_db(db_path)
_initialized: set[str] = set()


def now_iso() -> str:
    """Current UTC time as ISO-8601 string with 'Z' suffix (microsecond precision)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_id() -> str:
    return str(uuid.uuid4())


def get_db_path() -> str:
    """Resolve the active DB path: init_db override > DB_PATH env > <repo_root>/db/finally.db."""
    if _db_path:
        return _db_path
    env = os.environ.get("DB_PATH")
    if env:
        return env
    return str(_REPO_ROOT / "db" / "finally.db")


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _init_path(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        _seed(conn)
        conn.commit()
    finally:
        conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    """Seed default data if missing. Safe to run repeatedly."""
    ts = now_iso()
    cur = conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, ts),
    )
    # Only seed the watchlist when the user profile was freshly created, so a user
    # who removed every ticker doesn't get the defaults back on restart.
    if cur.rowcount == 1:
        conn.executemany(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            [(new_id(), DEFAULT_USER_ID, t, now_iso()) for t in DEFAULT_WATCHLIST],
        )


def init_db(db_path: str | None = None) -> None:
    """Idempotently create the schema and seed defaults.

    If ``db_path`` is given it becomes the active database for all subsequent calls.
    """
    global _db_path
    with _lock:
        if db_path is not None:
            _db_path = str(db_path)
        path = get_db_path()
        _init_path(path)
        _initialized.add(path)


def get_connection() -> sqlite3.Connection:
    """Open a new connection to the active DB (lazily initializing it on first use).

    Caller is responsible for closing it; it also works as a context manager for
    transactions (``with conn:`` commits/rolls back but does not close).
    """
    path = get_db_path()
    if path not in _initialized:
        with _lock:
            if path not in _initialized:
                _init_path(path)
                _initialized.add(path)
    return _connect(path)


def reset_for_tests() -> None:
    """Clear the path override and init cache (test helper)."""
    global _db_path
    with _lock:
        _db_path = None
        _initialized.clear()
