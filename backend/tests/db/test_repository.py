"""Tests for app.db repository functions."""

import pytest

import app.db as db


class TestCash:
    def test_get_set(self, db_path):
        assert db.get_cash_balance() == 10000.0
        db.set_cash_balance(5000.5)
        assert db.get_cash_balance() == 5000.5

    def test_other_user_created_on_demand(self, db_path):
        assert db.get_cash_balance("alice") == 10000.0
        db.set_cash_balance(1.0, user_id="alice")
        assert db.get_cash_balance("alice") == 1.0
        assert db.get_cash_balance() == 10000.0


class TestWatchlist:
    def test_add(self, db_path):
        assert db.add_watchlist_ticker("PYPL") is True
        assert db.get_watchlist()[-1] == "PYPL"

    def test_add_duplicate(self, db_path):
        assert db.add_watchlist_ticker("AAPL") is False
        assert db.get_watchlist().count("AAPL") == 1

    def test_remove(self, db_path):
        assert db.remove_watchlist_ticker("TSLA") is True
        assert "TSLA" not in db.get_watchlist()
        assert db.remove_watchlist_ticker("TSLA") is False

    def test_order_preserved(self, db_path):
        for t in ["ZZZ", "AAA", "MMM"]:
            db.add_watchlist_ticker(t)
        assert db.get_watchlist()[-3:] == ["ZZZ", "AAA", "MMM"]

    def test_readd_goes_to_end(self, db_path):
        db.remove_watchlist_ticker("AAPL")
        db.add_watchlist_ticker("AAPL")
        assert db.get_watchlist()[-1] == "AAPL"

    def test_per_user(self, db_path):
        assert db.get_watchlist("bob") == []
        assert db.add_watchlist_ticker("AAPL", user_id="bob") is True
        assert db.get_watchlist("bob") == ["AAPL"]


class TestPositions:
    def test_insert_and_get(self, db_path):
        db.upsert_position("AAPL", 10, 190.0)
        pos = db.get_position("AAPL")
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == 10.0
        assert pos["avg_cost"] == 190.0
        assert pos["updated_at"].endswith("Z")

    def test_update(self, db_path):
        db.upsert_position("AAPL", 10, 190.0)
        db.upsert_position("AAPL", 15, 195.0)
        assert len(db.get_positions()) == 1
        pos = db.get_position("AAPL")
        assert pos["quantity"] == 15.0 and pos["avg_cost"] == 195.0

    def test_zero_quantity_deletes(self, db_path):
        db.upsert_position("AAPL", 10, 190.0)
        db.upsert_position("AAPL", 0, 190.0)
        assert db.get_position("AAPL") is None
        assert db.get_positions() == []

    def test_float_dust_deletes(self, db_path):
        db.upsert_position("AAPL", 1e-12, 190.0)
        assert db.get_position("AAPL") is None

    def test_zero_on_missing_is_noop(self, db_path):
        db.upsert_position("AAPL", 0, 0)
        assert db.get_positions() == []

    def test_fractional(self, db_path):
        db.upsert_position("AAPL", 0.5, 100.0)
        assert db.get_position("AAPL")["quantity"] == 0.5

    def test_list(self, db_path):
        db.upsert_position("MSFT", 1, 1)
        db.upsert_position("AAPL", 2, 2)
        assert [p["ticker"] for p in db.get_positions()] == ["AAPL", "MSFT"]
        assert set(db.get_positions()[0]) == {"ticker", "quantity", "avg_cost", "updated_at"}

    def test_missing(self, db_path):
        assert db.get_position("NOPE") is None


class TestTrades:
    def test_record(self, db_path):
        t = db.record_trade("AAPL", "buy", 5, 190.12)
        assert set(t) == {"id", "ticker", "side", "quantity", "price", "executed_at"}
        assert t["ticker"] == "AAPL" and t["side"] == "buy"
        assert t["quantity"] == 5.0 and t["price"] == 190.12
        assert db.get_trades() == [t]

    def test_most_recent_first_and_limit(self, db_path):
        ids = [db.record_trade("AAPL", "buy", i + 1, 100)["id"] for i in range(5)]
        trades = db.get_trades(limit=3)
        assert [t["id"] for t in trades] == ids[::-1][:3]


class TestExecuteTradeAtomic:
    def test_buy_new_position(self, db_path):
        t = db.execute_trade_atomic("AAPL", "buy", 10, 100.0, 9000.0, 10, 100.0)
        assert db.get_cash_balance() == 9000.0
        assert db.get_position("AAPL")["quantity"] == 10.0
        assert db.get_trades() == [t]
        assert t["price"] == 100.0 and t["side"] == "buy"

    def test_sell_all_deletes_position(self, db_path):
        db.execute_trade_atomic("AAPL", "buy", 10, 100.0, 9000.0, 10, 100.0)
        db.execute_trade_atomic("AAPL", "sell", 10, 110.0, 10100.0, 0, 0)
        assert db.get_cash_balance() == 10100.0
        assert db.get_position("AAPL") is None
        assert len(db.get_trades()) == 2

    def test_rollback_on_failure(self, db_path):
        # Invalid side violates the CHECK constraint on the final insert,
        # so the cash and position changes must be rolled back.
        with pytest.raises(Exception):
            db.execute_trade_atomic("AAPL", "bogus", 10, 100.0, 1.0, 10, 100.0)
        assert db.get_cash_balance() == 10000.0
        assert db.get_position("AAPL") is None
        assert db.get_trades() == []


class TestSnapshots:
    def test_record_and_get_oldest_first(self, db_path):
        for v in [10000, 10100, 9900]:
            db.record_snapshot(v)
        snaps = db.get_snapshots()
        assert [s["total_value"] for s in snaps] == [10000.0, 10100.0, 9900.0]
        assert set(snaps[0]) == {"total_value", "recorded_at"}

    def test_limit_keeps_most_recent(self, db_path):
        for v in range(5):
            db.record_snapshot(v)
        assert [s["total_value"] for s in db.get_snapshots(limit=2)] == [3.0, 4.0]


class TestChat:
    def test_add_and_history(self, db_path):
        u = db.add_chat_message("user", "hi")
        a = db.add_chat_message("assistant", "hello", actions={"trades": [{"ticker": "AAPL"}]})
        assert u["actions"] is None
        hist = db.get_chat_history()
        assert [m["id"] for m in hist] == [u["id"], a["id"]]
        assert hist[1]["actions"] == {"trades": [{"ticker": "AAPL"}]}
        assert hist[0]["actions"] is None
        assert set(hist[0]) == {"id", "role", "content", "actions", "created_at"}

    def test_limit_keeps_most_recent_oldest_first(self, db_path):
        for i in range(5):
            db.add_chat_message("user", str(i))
        assert [m["content"] for m in db.get_chat_history(limit=3)] == ["2", "3", "4"]

    def test_empty_actions_dict_roundtrips(self, db_path):
        db.add_chat_message("assistant", "x", actions={})
        assert db.get_chat_history()[0]["actions"] == {}

    def test_invalid_role_rejected(self, db_path):
        with pytest.raises(Exception):
            db.add_chat_message("system", "x")

    def test_per_user(self, db_path):
        db.add_chat_message("user", "a", user_id="bob")
        assert db.get_chat_history() == []
        assert len(db.get_chat_history("bob")) == 1
