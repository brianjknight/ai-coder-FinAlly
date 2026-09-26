"""Tests for DB path resolution, lazy init, schema and seeding."""

import sqlite3
from pathlib import Path

import pytest

import app.db as db
from app.db import connection

EXPECTED_TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    connection.reset_for_tests()
    yield
    connection.reset_for_tests()


def _tables(path) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    finally:
        conn.close()
    return {r[0] for r in rows}


class TestPathResolution:
    def test_default_path_is_repo_root_db(self):
        expected = Path(__file__).resolve().parents[3] / "db" / "finally.db"
        assert Path(db.get_db_path()) == expected

    def test_env_var(self, tmp_path, monkeypatch):
        p = tmp_path / "env.db"
        monkeypatch.setenv("DB_PATH", str(p))
        assert db.get_db_path() == str(p)

    def test_init_db_arg_overrides_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DB_PATH", str(tmp_path / "env.db"))
        p = tmp_path / "arg.db"
        db.init_db(str(p))
        assert db.get_db_path() == str(p)
        assert p.exists()
        assert not (tmp_path / "env.db").exists()


class TestInit:
    def test_creates_parent_dir_and_tables(self, tmp_path):
        p = tmp_path / "a" / "b" / "finally.db"
        db.init_db(str(p))
        assert p.exists()
        assert EXPECTED_TABLES <= _tables(p)

    def test_lazy_init_via_env(self, tmp_path, monkeypatch):
        p = tmp_path / "lazy" / "finally.db"
        monkeypatch.setenv("DB_PATH", str(p))
        assert not p.exists()
        assert db.get_cash_balance() == 10000.0
        assert EXPECTED_TABLES <= _tables(p)
        assert db.get_watchlist() == db.DEFAULT_WATCHLIST

    def test_seed_defaults(self, tmp_path):
        db.init_db(str(tmp_path / "x.db"))
        assert db.get_cash_balance() == 10000.0
        assert db.get_watchlist() == [
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"
        ]
        assert db.get_positions() == []
        assert db.get_trades() == []
        assert db.get_snapshots() == []
        assert db.get_chat_history() == []

    def test_idempotent_does_not_reseed_or_reset(self, tmp_path):
        p = str(tmp_path / "x.db")
        db.init_db(p)
        db.set_cash_balance(123.0)
        db.remove_watchlist_ticker("AAPL")
        db.init_db(p)
        connection.reset_for_tests()
        db.init_db(p)
        assert db.get_cash_balance() == 123.0
        assert "AAPL" not in db.get_watchlist()
        assert len(db.get_watchlist()) == 9

    def test_empty_watchlist_not_reseeded(self, tmp_path):
        p = str(tmp_path / "x.db")
        db.init_db(p)
        for t in db.get_watchlist():
            db.remove_watchlist_ticker(t)
        connection.reset_for_tests()
        db.init_db(p)
        assert db.get_watchlist() == []

    def test_empty_existing_file_gets_initialized(self, tmp_path):
        p = tmp_path / "empty.db"
        p.touch()
        db.init_db(str(p))
        assert EXPECTED_TABLES <= _tables(p)
        assert len(db.get_watchlist()) == 10

    def test_wal_mode(self, tmp_path):
        p = tmp_path / "x.db"
        db.init_db(str(p))
        conn = sqlite3.connect(p)
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            conn.close()
        assert mode.lower() == "wal"

    def test_get_connection_row_factory(self, tmp_path):
        db.init_db(str(tmp_path / "x.db"))
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT id, cash_balance FROM users_profile").fetchone()
            assert isinstance(row, sqlite3.Row)
            assert row["id"] == "default"
        finally:
            conn.close()


class TestSchemaConstraints:
    def test_user_id_defaults(self, db_path):
        conn = db.get_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO trades (id, ticker, side, quantity, price, executed_at) "
                    "VALUES ('t1', 'AAPL', 'buy', 1, 1, 'x')"
                )
            row = conn.execute("SELECT user_id FROM trades WHERE id='t1'").fetchone()
            assert row["user_id"] == "default"
        finally:
            conn.close()

    def test_watchlist_unique(self, db_path):
        conn = db.get_connection()
        try:
            with pytest.raises(sqlite3.IntegrityError):
                with conn:
                    conn.execute(
                        "INSERT INTO watchlist (id, user_id, ticker, added_at) "
                        "VALUES ('w', 'default', 'AAPL', 'x')"
                    )
        finally:
            conn.close()

    def test_positions_unique(self, db_path):
        db.upsert_position("AAPL", 1, 1)
        conn = db.get_connection()
        try:
            with pytest.raises(sqlite3.IntegrityError):
                with conn:
                    conn.execute(
                        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, "
                        "updated_at) VALUES ('p', 'default', 'AAPL', 1, 1, 'x')"
                    )
        finally:
            conn.close()

    def test_trade_side_check(self, db_path):
        with pytest.raises(sqlite3.IntegrityError):
            db.record_trade("AAPL", "hold", 1, 1)
