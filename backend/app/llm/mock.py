<<<<<<< HEAD
"""Deterministic mock LLM responses (LLM_MOCK=true). E2E tests depend on these rules."""

from __future__ import annotations

import re

from .schemas import LLMResponse, TradeRequest, WatchlistChangeRequest

MOCK_DEFAULT_MESSAGE = "Mock response: I received your message."

_TICKER = r"([A-Za-z.]{1,10})(?![A-Za-z.])"
_TRADE_RE = re.compile(r"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+" + _TICKER, re.IGNORECASE)
_WATCH_RE = re.compile(r"\b(?:watch|add)\s+" + _TICKER, re.IGNORECASE)
# Words that follow "add"/"watch" in ordinary sentences and are not tickers.
_STOPWORDS = {"TO", "THE", "A", "AN", "IT", "ME", "MY", "SOME", "THIS", "THAT", "LIST"}


def mock_response(message: str) -> LLMResponse:
    trades = [
        TradeRequest(ticker=t.upper(), side=side.lower(), quantity=float(qty))
        for side, qty, t in _TRADE_RE.findall(message)
    ]
    changes: list[WatchlistChangeRequest] = []
    seen: set[str] = set()
    for t in _WATCH_RE.findall(message):
        ticker = t.upper()
        if ticker in _STOPWORDS or ticker in seen:
            continue
        seen.add(ticker)
        changes.append(WatchlistChangeRequest(ticker=ticker, action="add"))

    if not trades and not changes:
        return LLMResponse(message=MOCK_DEFAULT_MESSAGE, trades=[], watchlist_changes=[])

    parts = [f"{tr.side} {tr.quantity:g} {tr.ticker}" for tr in trades]
    parts += [f"add {c.ticker} to watchlist" for c in changes]
    return LLMResponse(
        message="Mock response: " + ", ".join(parts) + ".",
        trades=trades,
        watchlist_changes=changes,
    )
=======
"""Deterministic mock LLM responses for testing and development."""

import json

MOCK_RESPONSES = {
    "default": {
        "message": "I can see your portfolio. You have cash available. How can I help?",
        "trades": [],
        "watchlist_changes": [],
    },
    "buy": {
        "message": "Done! I've bought 5 shares of AAPL for you.",
        "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        "watchlist_changes": [],
    },
    "sell": {
        "message": "Done! I've sold 5 shares of AAPL for you.",
        "trades": [{"ticker": "AAPL", "side": "sell", "quantity": 5}],
        "watchlist_changes": [],
    },
    "add": {
        "message": "I've added PYPL to your watchlist.",
        "trades": [],
        "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
    },
    "remove": {
        "message": "I've removed PYPL from your watchlist.",
        "trades": [],
        "watchlist_changes": [{"ticker": "PYPL", "action": "remove"}],
    },
}


def get_mock_response(user_message: str) -> str:
    """Return a deterministic mock response based on keyword matching.

    Matches keywords in order: buy, sell, add/watch, remove, then default.
    """
    lower = user_message.lower()
    if "buy" in lower:
        key = "buy"
    elif "sell" in lower:
        key = "sell"
    elif "add" in lower or "watch" in lower:
        key = "add"
    elif "remove" in lower:
        key = "remove"
    else:
        key = "default"
    return json.dumps(MOCK_RESPONSES[key])
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
