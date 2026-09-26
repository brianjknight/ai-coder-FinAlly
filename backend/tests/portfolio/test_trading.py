"""Trade execution and valuation tests for app.portfolio."""

import pytest

from app import db
from app.portfolio import TradeError, execute_trade, get_portfolio


class TestBuy:
    def test_buy_deducts_cash_and_creates_position(self, cache):
        trade = execute_trade("AAPL", "buy", 10, cache)
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 10
        assert trade["price"] == 100.0
        assert {"id", "executed_at"} <= trade.keys()
        assert db.get_cash_balance() == pytest.approx(9000.0)
        pos = db.get_position("AAPL")
        assert pos["quantity"] == 10
        assert pos["avg_cost"] == 100.0

    def test_ticker_and_side_normalized(self, cache):
        trade = execute_trade(" aapl ", "BUY", 1, cache)
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"

    def test_weighted_average_cost(self, cache):
        execute_trade("AAPL", "buy", 10, cache)
        cache.update("AAPL", 130.0)
        execute_trade("AAPL", "buy", 5, cache)
        pos = db.get_position("AAPL")
        assert pos["quantity"] == 15
        assert pos["avg_cost"] == pytest.approx((10 * 100 + 5 * 130) / 15)

    def test_fractional_buy(self, cache):
        execute_trade("AAPL", "buy", 0.5, cache)
        assert db.get_position("AAPL")["quantity"] == 0.5
        assert db.get_cash_balance() == pytest.approx(9950.0)

    def test_insufficient_cash(self, cache):
        with pytest.raises(TradeError, match="Insufficient cash"):
            execute_trade("AAPL", "buy", 101, cache)
        assert db.get_cash_balance() == 10000.0
        assert db.get_position("AAPL") is None
        assert db.get_trades() == []

    def test_buy_exactly_all_cash(self, cache):
        execute_trade("AAPL", "buy", 100, cache)
        assert db.get_cash_balance() == pytest.approx(0.0)


class TestSell:
    def test_sell_partial_keeps_avg_cost(self, cache):
        execute_trade("AAPL", "buy", 10, cache)
        cache.update("AAPL", 120.0)
        execute_trade("AAPL", "sell", 4, cache)
        pos = db.get_position("AAPL")
        assert pos["quantity"] == 6
        assert pos["avg_cost"] == 100.0
        assert db.get_cash_balance() == pytest.approx(9000 + 480)

    def test_sell_all_removes_position(self, cache):
        execute_trade("AAPL", "buy", 10, cache)
        execute_trade("AAPL", "sell", 10, cache)
        assert db.get_position("AAPL") is None
        assert db.get_cash_balance() == pytest.approx(10000.0)

    def test_sell_at_loss(self, cache):
        execute_trade("AAPL", "buy", 10, cache)
        cache.update("AAPL", 80.0)
        execute_trade("AAPL", "sell", 10, cache)
        assert db.get_cash_balance() == pytest.approx(9800.0)

    def test_sell_full_fractional_position_with_float_noise(self, cache):
        execute_trade("AAPL", "buy", 0.1, cache)
        execute_trade("AAPL", "buy", 0.2, cache)  # 0.30000000000000004 held
        execute_trade("AAPL", "sell", 0.3, cache)
        assert db.get_position("AAPL") is None

    def test_sell_more_than_owned(self, cache):
        execute_trade("AAPL", "buy", 5, cache)
        with pytest.raises(TradeError, match="Insufficient shares"):
            execute_trade("AAPL", "sell", 6, cache)
        assert db.get_position("AAPL")["quantity"] == 5

    def test_sell_without_position(self, cache):
        with pytest.raises(TradeError, match="Insufficient shares"):
            execute_trade("AAPL", "sell", 1, cache)


class TestValidation:
    @pytest.mark.parametrize("qty", [0, -1, "abc", None, float("nan"), float("inf")])
    def test_bad_quantity(self, cache, qty):
        with pytest.raises(TradeError):
            execute_trade("AAPL", "buy", qty, cache)

    def test_bad_side(self, cache):
        with pytest.raises(TradeError, match="Side"):
            execute_trade("AAPL", "hold", 1, cache)

    @pytest.mark.parametrize("ticker", ["", "AAPL1", "TOOLONGTICKER", None])
    def test_bad_ticker(self, cache, ticker):
        with pytest.raises(TradeError, match="Invalid ticker"):
            execute_trade(ticker, "buy", 1, cache)

    def test_no_price(self, cache):
        with pytest.raises(TradeError, match="No price available for ZZZ"):
            execute_trade("ZZZ", "buy", 1, cache)


class TestSnapshotsAndTrades:
    def test_trade_logged_and_snapshot_recorded(self, cache):
        execute_trade("AAPL", "buy", 10, cache)
        execute_trade("AAPL", "sell", 3, cache)
        trades = db.get_trades()
        assert [t["side"] for t in trades] == ["sell", "buy"]
        snaps = db.get_snapshots()
        assert len(snaps) == 2
        assert snaps[-1]["total_value"] == pytest.approx(10000.0)


class TestGetPortfolio:
    def test_empty(self, cache):
        p = get_portfolio(cache)
        assert p == {
            "cash_balance": 10000.0,
            "total_value": 10000.0,
            "positions_value": 0.0,
            "unrealized_pnl": 0.0,
            "positions": [],
        }

    def test_pnl_math(self, cache):
        execute_trade("AAPL", "buy", 10, cache)
        execute_trade("MSFT", "buy", 5, cache)
        cache.update("AAPL", 110.0)
        cache.update("MSFT", 190.0)
        p = get_portfolio(cache)
        assert p["cash_balance"] == pytest.approx(8000.0)
        assert p["positions_value"] == pytest.approx(1100 + 950)
        assert p["total_value"] == pytest.approx(8000 + 2050)
        assert p["unrealized_pnl"] == pytest.approx(100 - 50)
        by_ticker = {x["ticker"]: x for x in p["positions"]}
        assert by_ticker["AAPL"] == {
            "ticker": "AAPL",
            "quantity": 10,
            "avg_cost": 100.0,
            "current_price": 110.0,
            "market_value": 1100.0,
            "unrealized_pnl": 100.0,
            "pnl_percent": 10.0,
        }
        assert by_ticker["MSFT"]["pnl_percent"] == pytest.approx(-5.0)

    def test_missing_price_falls_back_to_avg_cost(self, cache):
        execute_trade("AAPL", "buy", 10, cache)
        cache.remove("AAPL")
        pos = get_portfolio(cache)["positions"][0]
        assert pos["current_price"] == 100.0
        assert pos["unrealized_pnl"] == 0.0
