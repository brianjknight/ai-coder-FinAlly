<<<<<<< HEAD
"""FinAlly persistence layer (SQLite). See planning/TEAM_CONTRACTS.md "DB module API"."""

from .connection import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST,
    get_connection,
    get_db_path,
    init_db,
)
from .repository import (
    add_chat_message,
    add_watchlist_ticker,
    execute_trade_atomic,
    get_cash_balance,
    get_chat_history,
    get_position,
    get_positions,
    get_snapshots,
    get_trades,
    get_watchlist,
    record_snapshot,
    record_trade,
    remove_watchlist_ticker,
    set_cash_balance,
    upsert_position,
)

__all__ = [
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_USER_ID",
    "DEFAULT_WATCHLIST",
    "add_chat_message",
    "add_watchlist_ticker",
    "execute_trade_atomic",
    "get_cash_balance",
    "get_chat_history",
    "get_connection",
    "get_db_path",
    "get_position",
    "get_positions",
    "get_snapshots",
    "get_trades",
    "get_watchlist",
    "init_db",
    "record_snapshot",
    "record_trade",
    "remove_watchlist_ticker",
    "set_cash_balance",
    "upsert_position",
]
=======
"""Database layer for FinAlly.

Public API:
    init_db   - Initialize database with schema and seed data
    close_db  - Close the database connection
"""

from .connection import close_db, init_db

__all__ = ["init_db", "close_db"]
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
