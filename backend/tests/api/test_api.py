"""REST API tests: status codes and response shapes per planning/TEAM_CONTRACTS.md."""

import pytest
from fastapi.testclient import TestClient

from app import main

PORTFOLIO_KEYS = {"cash_balance", "total_value", "positions_value", "unrealized_pnl", "positions"}
POSITION_KEYS = {
    "ticker", "quantity", "avg_cost", "current_price", "market_value", "unrealized_pnl",
    "pnl_percent",
}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


class TestPortfolio:
    def test_initial_portfolio(self, client):
        r = client.get("/api/portfolio")
        assert r.status_code == 200
        body = r.json()
        assert set(body) == PORTFOLIO_KEYS
        assert body["cash_balance"] == 10000.0
        assert body["total_value"] == 10000.0
        assert body["positions"] == []

    def test_buy(self, client):
        r = client.post("/api/portfolio/trade", json={"ticker": "aapl", "quantity": 10, "side": "buy"})
        assert r.status_code == 200
        body = r.json()
        assert set(body["trade"]) == {"id", "ticker", "side", "quantity", "price", "executed_at"}
        assert body["trade"]["ticker"] == "AAPL"
        assert body["trade"]["price"] == 100.0
        pf = body["portfolio"]
        assert set(pf) == PORTFOLIO_KEYS
        assert pf["cash_balance"] == 9000.0
        assert len(pf["positions"]) == 1
        assert set(pf["positions"][0]) == POSITION_KEYS

    def test_sell_all(self, client):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 2, "side": "buy"})
        r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 2, "side": "sell"})
        assert r.status_code == 200
        assert r.json()["portfolio"]["positions"] == []
        assert r.json()["portfolio"]["cash_balance"] == 10000.0

    @pytest.mark.parametrize(
        "payload,msg",
        [
            ({"ticker": "AAPL", "quantity": 1000, "side": "buy"}, "Insufficient cash"),
            ({"ticker": "AAPL", "quantity": 1, "side": "sell"}, "Insufficient shares"),
            ({"ticker": "AAPL", "quantity": 0, "side": "buy"}, "Quantity"),
            ({"ticker": "AAPL", "quantity": 1, "side": "short"}, "Side"),
            ({"ticker": "ZZZZ", "quantity": 1, "side": "buy"}, "No price"),
            ({"ticker": "12", "quantity": 1, "side": "buy"}, "Invalid ticker"),
        ],
    )
    def test_trade_errors(self, client, payload, msg):
        r = client.post("/api/portfolio/trade", json=payload)
        assert r.status_code == 400
        assert msg in r.json()["detail"]

    def test_missing_field_gives_string_detail(self, client):
        r = client.post("/api/portfolio/trade", json={"ticker": "AAPL"})
        assert r.status_code == 422
        assert isinstance(r.json()["detail"], str)

    def test_history(self, client):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
        r = client.get("/api/portfolio/history")
        assert r.status_code == 200
        snaps = r.json()["snapshots"]
        # startup baseline + post-trade snapshot
        assert len(snaps) >= 2
        assert set(snaps[0]) == {"total_value", "recorded_at"}


class TestWatchlist:
    def test_default_watchlist(self, client):
        r = client.get("/api/watchlist")
        assert r.status_code == 200
        tickers = r.json()["tickers"]
        assert [t["ticker"] for t in tickers][:3] == ["AAPL", "GOOGL", "MSFT"]
        assert len(tickers) == 10
        assert set(tickers[0]) == {
            "ticker", "price", "previous_price", "change", "change_percent", "direction",
        }
        assert tickers[0]["price"] == 100.0

    def test_add_and_remove(self, client, app):
        r = client.post("/api/watchlist", json={"ticker": "pypl"})
        assert r.status_code == 201
        assert r.json() == {"ticker": "PYPL"}
        assert "PYPL" in app.state.market_source.get_tickers()
        listed = [t["ticker"] for t in client.get("/api/watchlist").json()["tickers"]]
        assert listed[-1] == "PYPL"

        r = client.delete("/api/watchlist/pypl")
        assert r.status_code == 200
        assert r.json() == {"ticker": "PYPL"}
        assert "PYPL" not in app.state.market_source.get_tickers()

    def test_add_duplicate(self, client):
        assert client.post("/api/watchlist", json={"ticker": "AAPL"}).status_code == 409

    def test_add_invalid(self, client):
        r = client.post("/api/watchlist", json={"ticker": "BAD1"})
        assert r.status_code == 400
        assert "Invalid" in r.json()["detail"]

    def test_remove_missing(self, client):
        assert client.delete("/api/watchlist/ZZZ").status_code == 404

    def test_remove_held_ticker_keeps_price(self, client, app):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
        assert client.delete("/api/watchlist/AAPL").status_code == 200
        assert "AAPL" in app.state.market_source.get_tickers()
        pos = client.get("/api/portfolio").json()["positions"][0]
        assert pos["current_price"] == 100.0


class TestChat:
    def test_history_empty(self, client):
        r = client.get("/api/chat/history")
        assert r.status_code == 200
        assert r.json() == {"messages": []}

    def test_empty_message_rejected(self, client):
        assert client.post("/api/chat", json={"message": "   "}).status_code == 400

    def test_chat_delegates_to_handle_chat(self, client, monkeypatch):
        import app.llm as llm

        calls = []

        async def fake_handle_chat(message, price_cache, source):
            calls.append((message, price_cache, source))
            return {"message": "hi", "trades": [], "watchlist_changes": []}

        monkeypatch.setattr(llm, "handle_chat", fake_handle_chat)
        r = client.post("/api/chat", json={"message": "hello"})
        assert r.status_code == 200
        assert r.json() == {"message": "hi", "trades": [], "watchlist_changes": []}
        assert calls[0][0] == "hello"
        assert calls[0][1] is client.app.state.price_cache

    def test_mock_chat_end_to_end(self, client):
        r = client.post("/api/chat", json={"message": "hello there"})
        assert r.status_code == 200
        body = r.json()
        assert set(body) >= {"message", "trades", "watchlist_changes"}
        msgs = client.get("/api/chat/history").json()["messages"]
        assert [m["role"] for m in msgs] == ["user", "assistant"]
        assert set(msgs[0]) == {"id", "role", "content", "actions", "created_at"}

    def test_mock_chat_buy(self, client):
        r = client.post("/api/chat", json={"message": "please buy 2 AAPL"})
        assert r.status_code == 200
        trades = r.json()["trades"]
        assert trades and trades[0]["status"] == "executed"
        assert client.get("/api/portfolio").json()["cash_balance"] == 9800.0


def test_lifespan_stops_source(app):
    with TestClient(app):
        source = app.state.market_source
    assert source.stopped


def test_static_files_served(tmp_path, monkeypatch, app):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>FinAlly</html>")
    monkeypatch.setenv("STATIC_DIR", str(static))
    with TestClient(main.create_app()) as c:
        assert "FinAlly" in c.get("/").text
        assert c.get("/api/health").json() == {"status": "ok"}
