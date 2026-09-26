"""Tests for the LLM chat module (schema, mock rules, LLM call handling, auto-execution)."""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app import db
from app.llm import client, handle_chat, service
from app.llm.mock import MOCK_DEFAULT_MESSAGE, mock_response
from app.llm.prompt import SYSTEM_PROMPT, build_context, build_messages
from app.llm.schemas import LLMResponse


def _completion_returning(content):
    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    fake_completion.calls = calls
    return fake_completion


# ---------------------------------------------------------------- schema


class TestSchema:
    def test_full_payload(self):
        r = LLMResponse.model_validate_json(
            json.dumps(
                {
                    "message": "ok",
                    "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1.5}],
                    "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
                }
            )
        )
        assert r.trades[0].quantity == 1.5
        assert r.watchlist_changes[0].action == "add"

    def test_message_only_defaults_to_empty_lists(self):
        r = LLMResponse.model_validate_json('{"message": "hi"}')
        assert r.trades == [] and r.watchlist_changes == []

    @pytest.mark.parametrize(
        "payload",
        [
            "not json",
            "{}",
            '{"message": "x", "trades": [{"ticker": "AAPL", "side": "hold", "quantity": 1}]}',
            '{"message": "x", "watchlist_changes": [{"ticker": "AAPL", "action": "delete"}]}',
        ],
    )
    def test_invalid_payloads_raise(self, payload):
        with pytest.raises(ValidationError):
            LLMResponse.model_validate_json(payload)


# ---------------------------------------------------------------- mock rules


class TestMockRules:
    def test_default(self):
        r = mock_response("hello there")
        assert r.model_dump() == {
            "message": MOCK_DEFAULT_MESSAGE,
            "trades": [],
            "watchlist_changes": [],
        }

    def test_buy_case_insensitive(self):
        r = mock_response("Please BUY 5 aapl now")
        assert [(t.ticker, t.side, t.quantity) for t in r.trades] == [("AAPL", "buy", 5.0)]

    def test_sell_fractional(self):
        r = mock_response("sell 2.5 MSFT")
        assert [(t.ticker, t.side, t.quantity) for t in r.trades] == [("MSFT", "sell", 2.5)]

    def test_watch_and_add(self):
        r = mock_response("watch PYPL and add uber")
        assert [(c.ticker, c.action) for c in r.watchlist_changes] == [
            ("PYPL", "add"),
            ("UBER", "add"),
        ]

    def test_add_to_watchlist_phrase_ignored(self):
        assert mock_response("add to my watchlist").watchlist_changes == []

    def test_combined(self):
        r = mock_response("buy 1 AAPL, sell 2 MSFT, watch PYPL")
        assert len(r.trades) == 2 and len(r.watchlist_changes) == 1


# ---------------------------------------------------------------- prompt


class TestPrompt:
    def test_context_contains_portfolio_and_prices(self, price_cache):
        portfolio = {
            "cash_balance": 5000.123,
            "total_value": 6900.0,
            "positions_value": 1900.0,
            "unrealized_pnl": 10.0,
            "positions": [
                {
                    "ticker": "AAPL",
                    "quantity": 10,
                    "avg_cost": 189.0,
                    "current_price": 190.0,
                    "market_value": 1900.0,
                    "unrealized_pnl": 10.0,
                    "pnl_percent": 0.529,
                }
            ],
        }
        ctx = build_context(portfolio, ["AAPL", "ZZZZ"], price_cache)
        data = json.loads(ctx.split("\n", 1)[1])
        assert data["cash_balance"] == 5000.12
        assert data["positions"][0]["ticker"] == "AAPL"
        assert data["watchlist"][0]["price"] == 190.0
        assert data["watchlist"][1]["price"] is None

    def test_messages_order(self):
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        msgs = build_messages("CTX", history, "buy stuff")
        assert msgs[0] == {"role": "system", "content": SYSTEM_PROMPT}
        assert "FinAlly" in SYSTEM_PROMPT
        assert [m["content"] for m in msgs[1:]] == ["CTX", "hi", "hello", "buy stuff"]


# ---------------------------------------------------------------- LLM client


class TestClient:
    async def test_call_uses_cerebras_settings(self, monkeypatch):
        fake = _completion_returning('{"message": "hi", "trades": [], "watchlist_changes": []}')
        monkeypatch.setattr(client, "completion", fake)
        r = await client.call_llm([{"role": "user", "content": "x"}])
        assert r.message == "hi"
        kw = fake.calls[0]
        assert kw["model"] == "openrouter/openai/gpt-oss-120b"
        assert kw["extra_body"] == {"provider": {"order": ["cerebras"]}}
        assert kw["response_format"] is LLMResponse
        assert kw["reasoning_effort"] == "low"

    async def test_empty_content_raises(self, monkeypatch):
        monkeypatch.setattr(client, "completion", _completion_returning(None))
        with pytest.raises(ValueError):
            await client.call_llm([])


# ---------------------------------------------------------------- handle_chat


class TestHandleChatMock:
    async def test_default_response_shape(self, mock_mode, price_cache, source):
        r = await handle_chat("hello", price_cache, source)
        assert r == {"message": MOCK_DEFAULT_MESSAGE, "trades": [], "watchlist_changes": []}

    async def test_buy_executes(self, mock_mode, price_cache, source):
        r = await handle_chat("buy 5 AAPL", price_cache, source)
        assert r["trades"] == [
            {
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 5.0,
                "status": "executed",
                "price": 190.0,
                "error": None,
            }
        ]
        assert db.get_position("AAPL")["quantity"] == 5.0
        assert db.get_cash_balance() == pytest.approx(10000 - 5 * 190.0)

    async def test_sell_without_shares_fails(self, mock_mode, price_cache, source):
        r = await handle_chat("sell 3 AAPL", price_cache, source)
        t = r["trades"][0]
        assert t["status"] == "failed" and t["error"].startswith("Insufficient shares")
        assert t["price"] is None
        assert "Insufficient shares" in r["message"]
        assert db.get_trades() == []

    async def test_watch_adds_to_db_and_source(
        self, mock_mode, price_cache, source
    ):
        r = await handle_chat("watch PYPL", price_cache, source)
        assert r["watchlist_changes"] == [
            {"ticker": "PYPL", "action": "add", "status": "executed", "error": None}
        ]
        assert "PYPL" in db.get_watchlist()
        assert source.added == ["PYPL"]

    async def test_watch_existing_fails(self, mock_mode, price_cache, source):
        r = await handle_chat("add AAPL", price_cache, source)
        c = r["watchlist_changes"][0]
        assert c["status"] == "failed" and "already" in c["error"]

    async def test_messages_persisted(self, mock_mode, price_cache, source):
        await handle_chat("buy 1 AAPL", price_cache, source)
        hist = db.get_chat_history()
        assert [m["role"] for m in hist] == ["user", "assistant"]
        assert hist[0]["content"] == "buy 1 AAPL" and hist[0]["actions"] is None
        assert hist[1]["actions"]["trades"][0]["status"] == "executed"
        assert hist[1]["actions"]["watchlist_changes"] == []

    async def test_mock_never_calls_llm(self, mock_mode, price_cache, source,
                                        monkeypatch):
        def boom(**kwargs):
            raise AssertionError("completion must not be called in mock mode")

        monkeypatch.setattr(client, "completion", boom)
        r = await handle_chat("hi", price_cache, source)
        assert r["message"] == MOCK_DEFAULT_MESSAGE


class TestHandleChatLive:
    async def test_structured_response_executes_actions(
        self, live_mode, price_cache, source, monkeypatch
    ):
        payload = {
            "message": "Buying and watching.",
            "trades": [
                {"ticker": "aapl", "side": "buy", "quantity": 2},
                {"ticker": "MSFT", "side": "buy", "quantity": 1000},
                {"ticker": "NOPE", "side": "buy", "quantity": 1},
            ],
            "watchlist_changes": [
                {"ticker": "PYPL", "action": "add"},
                {"ticker": "NFLX", "action": "remove"},
                {"ticker": "bad ticker!", "action": "add"},
            ],
        }
        fake = _completion_returning(json.dumps(payload))
        monkeypatch.setattr(client, "completion", fake)

        r = await handle_chat("do it", price_cache, source)

        statuses = [(t["ticker"], t["status"]) for t in r["trades"]]
        assert statuses == [("AAPL", "executed"), ("MSFT", "failed"), ("NOPE", "failed")]
        assert r["trades"][1]["error"].startswith("Insufficient cash")
        assert db.get_position("AAPL")["quantity"] == 2
        wl = [(c["ticker"], c["action"], c["status"]) for c in r["watchlist_changes"]]
        assert wl == [
            ("PYPL", "add", "executed"),
            ("NFLX", "remove", "executed"),
            ("BAD TICKER!", "add", "failed"),
        ]
        assert source.removed == ["NFLX"]
        assert r["message"].startswith("Buying and watching.")
        assert "Insufficient cash" in r["message"]

        # prompt included system prompt, context and user message
        msgs = fake.calls[0]["messages"]
        assert msgs[0]["content"] == SYSTEM_PROMPT
        assert '"cash_balance": 10000.0' in msgs[1]["content"]
        assert msgs[-1] == {"role": "user", "content": "do it"}

    async def test_history_included_in_prompt(
        self, live_mode, price_cache, source, monkeypatch
    ):
        db.add_chat_message("user", "earlier question")
        db.add_chat_message("assistant", "earlier answer", actions={"trades": []})
        fake = _completion_returning('{"message": "ok", "trades": [], "watchlist_changes": []}')
        monkeypatch.setattr(client, "completion", fake)
        await handle_chat("new question", price_cache, source)
        contents = [m["content"] for m in fake.calls[0]["messages"]]
        assert contents[-3:] == ["earlier question", "earlier answer", "new question"]

    @pytest.mark.parametrize("content", ["not json at all", '{"trades": []}', None])
    async def test_malformed_output_is_graceful(
        self, live_mode, price_cache, source, monkeypatch, content
    ):
        monkeypatch.setattr(client, "completion", _completion_returning(content))
        r = await handle_chat("hi", price_cache, source)
        assert r == {"message": service.ERROR_MESSAGE, "trades": [], "watchlist_changes": []}
        assert db.get_trades() == []
        # the exchange is still recorded
        assert [m["role"] for m in db.get_chat_history()] == ["user", "assistant"]

    async def test_network_error_is_graceful(
        self, live_mode, price_cache, source, monkeypatch
    ):
        def boom(**kwargs):
            raise ConnectionError("network down")

        monkeypatch.setattr(client, "completion", boom)
        r = await handle_chat("hi", price_cache, source)
        assert r["message"] == service.ERROR_MESSAGE
        assert r["trades"] == [] and r["watchlist_changes"] == []

    async def test_missing_api_key(self, price_cache, source, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "false")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        r = await handle_chat("hi", price_cache, source)
        assert r["message"] == service.NO_KEY_MESSAGE

    async def test_unexpected_trade_exception_is_contained(
        self, live_mode, price_cache, source, monkeypatch
    ):
        def explode(*a, **k):
            raise RuntimeError("db locked")

        monkeypatch.setattr(service.portfolio, "execute_trade", explode)
        payload = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1}]}'
        monkeypatch.setattr(client, "completion", _completion_returning(payload))
        r = await handle_chat("buy", price_cache, source)
        assert r["trades"][0]["status"] == "failed"
        assert r["trades"][0]["error"] == "db locked"
