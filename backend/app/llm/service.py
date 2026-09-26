"""Chat orchestration: context -> LLM (or mock) -> auto-execute actions -> persist."""

from __future__ import annotations

import logging
import os

from app import db, portfolio

from . import client, mock
from .prompt import build_context, build_messages
from .schemas import LLMResponse

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20
ERROR_MESSAGE = (
    "Sorry, I couldn't reach the AI service or understand its reply just now. "
    "Please try again in a moment."
)
NO_KEY_MESSAGE = (
    "The AI assistant isn't configured (OPENROUTER_API_KEY is missing). "
    "You can still trade manually, or set LLM_MOCK=true for mock responses."
)


def is_mock_mode() -> bool:
    return os.getenv("LLM_MOCK", "").strip().lower() in ("1", "true", "yes", "on")


async def _get_llm_response(message: str, price_cache) -> LLMResponse:
    if is_mock_mode():
        return mock.mock_response(message)
    if not os.getenv("OPENROUTER_API_KEY"):
        return LLMResponse(message=NO_KEY_MESSAGE)
    try:
        snapshot = portfolio.get_portfolio(price_cache)
        context = build_context(snapshot, db.get_watchlist(), price_cache)
        history = db.get_chat_history(limit=HISTORY_LIMIT)
        messages = build_messages(context, history, message)
        return await client.call_llm(messages)
    except Exception:
        logger.exception("LLM call failed")
        return LLMResponse(message=ERROR_MESSAGE)


def _execute_trades(resp: LLMResponse, price_cache) -> list[dict]:
    results = []
    for t in resp.trades:
        ticker = t.ticker.strip().upper()
        result = {
            "ticker": ticker,
            "side": t.side,
            "quantity": t.quantity,
            "status": "failed",
            "price": None,
            "error": None,
        }
        try:
            trade = portfolio.execute_trade(ticker, t.side, t.quantity, price_cache)
            result["status"] = "executed"
            result["ticker"] = trade.get("ticker", ticker)
            result["quantity"] = trade.get("quantity", t.quantity)
            result["price"] = trade.get("price")
        except portfolio.TradeError as e:
            result["error"] = str(e) or "Trade failed"
        except Exception as e:  # never let one bad action break the chat
            logger.exception("Unexpected error executing LLM trade %s", t)
            result["error"] = str(e) or "Trade failed"
        results.append(result)
    return results


async def _execute_watchlist_changes(resp: LLMResponse, source) -> list[dict]:
    results = []
    for c in resp.watchlist_changes:
        ticker = c.ticker.strip().upper()
        result = {"ticker": ticker, "action": c.action, "status": "failed", "error": None}
        try:
            if c.action == "add":
                result["ticker"] = await portfolio.add_to_watchlist(ticker, source)
            else:
                result["ticker"] = await portfolio.remove_from_watchlist(ticker, source)
            result["status"] = "executed"
        except portfolio.WatchlistError as e:
            result["error"] = str(e) or "Watchlist change failed"
        except Exception as e:
            logger.exception("Unexpected error applying watchlist change %s", c)
            result["error"] = str(e) or "Watchlist change failed"
        results.append(result)
    return results


def _failure_note(trades: list[dict], changes: list[dict]) -> str:
    notes = [
        f"{t['side']} {t['quantity']:g} {t['ticker']} failed: {t['error']}"
        for t in trades
        if t["status"] == "failed"
    ]
    notes += [
        f"watchlist {c['action']} {c['ticker']} failed: {c['error']}"
        for c in changes
        if c["status"] == "failed"
    ]
    return ("\n\nNote: " + "; ".join(notes) + ".") if notes else ""


async def handle_chat(message: str, price_cache, source) -> dict:
    """Process one user chat message. Returns the POST /api/chat response shape."""
    resp = await _get_llm_response(message, price_cache)

    trades = _execute_trades(resp, price_cache)
    changes = await _execute_watchlist_changes(resp, source)
    reply = resp.message + _failure_note(trades, changes)

    actions = {"trades": trades, "watchlist_changes": changes}
    try:
        db.add_chat_message("user", message)
        db.add_chat_message("assistant", reply, actions=actions)
    except Exception:
        logger.exception("Failed to persist chat messages")

    return {"message": reply, "trades": trades, "watchlist_changes": changes}
