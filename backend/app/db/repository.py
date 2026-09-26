"""Repository functions for all FinAlly tables. Plain sqlite3, one connection per call."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .connection import DEFAULT_CASH_BALANCE, get_connection, new_id, now_iso

_EPSILON = 1e-9


@contextmanager
def _transaction() -> Iterator[sqlite3.Connection]:
    """Connection that commits on success, rolls back on error, and always closes."""
    conn = get_connection()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


# --- users_profile -----------------------------------------------------------


def _ensure_user(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (user_id, DEFAULT_CASH_BALANCE, now_iso()),
    )


def get_cash_balance(user_id: str = "default") -> float:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            _ensure_user(conn, user_id)
            return DEFAULT_CASH_BALANCE
        return float(row["cash_balance"])


def _set_cash(conn: sqlite3.Connection, cash: float, user_id: str) -> None:
    _ensure_user(conn, user_id)
    conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (float(cash), user_id))


def set_cash_balance(cash: float, user_id: str = "default") -> None:
    with _transaction() as conn:
        _set_cash(conn, cash, user_id)


# --- watchlist ---------------------------------------------------------------


def get_watchlist(user_id: str = "default") -> list[str]:
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid",
            (user_id,),
        ).fetchall()
    return [r["ticker"] for r in rows]


def add_watchlist_ticker(ticker: str, user_id: str = "default") -> bool:
    """Add a ticker. Returns False if it was already present."""
    with _transaction() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (new_id(), user_id, ticker, now_iso()),
        )
        return cur.rowcount == 1


def remove_watchlist_ticker(ticker: str, user_id: str = "default") -> bool:
    """Remove a ticker. Returns False if it was not present."""
    with _transaction() as conn:
        cur = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
        )
        return cur.rowcount > 0


# --- positions ---------------------------------------------------------------


def _position_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "ticker": row["ticker"],
        "quantity": float(row["quantity"]),
        "avg_cost": float(row["avg_cost"]),
        "updated_at": row["updated_at"],
    }


def get_positions(user_id: str = "default") -> list[dict]:
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions "
            "WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    return [_position_dict(r) for r in rows]


def get_position(ticker: str, user_id: str = "default") -> dict | None:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions "
            "WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
    return _position_dict(row) if row else None


def _upsert_position(
    conn: sqlite3.Connection, ticker: str, quantity: float, avg_cost: float, user_id: str
) -> None:
    if abs(quantity) < _EPSILON:
        conn.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker))
        return
    conn.execute(
        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (user_id, ticker) DO UPDATE SET "
        "quantity = excluded.quantity, avg_cost = excluded.avg_cost, "
        "updated_at = excluded.updated_at",
        (new_id(), user_id, ticker, float(quantity), float(avg_cost), now_iso()),
    )


def upsert_position(
    ticker: str, quantity: float, avg_cost: float, user_id: str = "default"
) -> None:
    """Insert or update a position; quantity == 0 (within 1e-9) deletes the row."""
    with _transaction() as conn:
        _upsert_position(conn, ticker, quantity, avg_cost, user_id)


# --- trades ------------------------------------------------------------------


def _insert_trade(
    conn: sqlite3.Connection, ticker: str, side: str, quantity: float, price: float, user_id: str
) -> dict[str, Any]:
    trade = {
        "id": new_id(),
        "ticker": ticker,
        "side": side,
        "quantity": float(quantity),
        "price": float(price),
        "executed_at": now_iso(),
    }
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trade["id"], user_id, ticker, side, trade["quantity"], trade["price"],
         trade["executed_at"]),
    )
    return trade


def record_trade(
    ticker: str, side: str, quantity: float, price: float, user_id: str = "default"
) -> dict:
    """Append a trade to the log. Returns {id, ticker, side, quantity, price, executed_at}."""
    with _transaction() as conn:
        return _insert_trade(conn, ticker, side, quantity, price, user_id)


def get_trades(user_id: str = "default", limit: int = 100) -> list[dict]:
    """Most recent trades first."""
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT id, ticker, side, quantity, price, executed_at FROM trades "
            "WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def execute_trade_atomic(
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    new_cash: float,
    new_quantity: float,
    new_avg_cost: float,
    user_id: str = "default",
) -> dict:
    """Set cash, upsert/delete the position and insert the trade in ONE transaction.

    Validation (sufficient cash/shares) is the caller's job. Returns the trade dict.
    """
    with _transaction() as conn:
        _set_cash(conn, new_cash, user_id)
        _upsert_position(conn, ticker, new_quantity, new_avg_cost, user_id)
        return _insert_trade(conn, ticker, side, quantity, price, user_id)


# --- portfolio_snapshots -----------------------------------------------------


def record_snapshot(total_value: float, user_id: str = "default") -> None:
    with _transaction() as conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (new_id(), user_id, float(total_value), now_iso()),
        )


def get_snapshots(user_id: str = "default", limit: int = 1000) -> list[dict]:
    """The most recent ``limit`` snapshots, returned oldest first."""
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at DESC, rowid DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"total_value": float(r["total_value"]), "recorded_at": r["recorded_at"]}
            for r in reversed(rows)]


# --- chat_messages -----------------------------------------------------------


def _parse_actions(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def add_chat_message(
    role: str, content: str, actions: dict | None = None, user_id: str = "default"
) -> dict:
    """Store a chat message. Returns {id, role, content, actions, created_at}."""
    msg = {
        "id": new_id(),
        "role": role,
        "content": content,
        "actions": actions,
        "created_at": now_iso(),
    }
    with _transaction() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg["id"], user_id, role, content,
             json.dumps(actions) if actions is not None else None, msg["created_at"]),
        )
    return msg


def get_chat_history(user_id: str = "default", limit: int = 20) -> list[dict]:
    """The most recent ``limit`` messages, returned oldest first, actions parsed from JSON."""
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT id, role, content, actions, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "actions": _parse_actions(r["actions"]),
            "created_at": r["created_at"],
        }
        for r in reversed(rows)
    ]
