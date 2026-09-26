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
