"""Pydantic models for the LLM structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TradeRequest(BaseModel):
    ticker: str = Field(description="Stock ticker symbol, e.g. AAPL")
    side: Literal["buy", "sell"]
    quantity: float = Field(description="Number of shares (> 0, fractional allowed)")


class WatchlistChangeRequest(BaseModel):
    ticker: str = Field(description="Stock ticker symbol, e.g. PYPL")
    action: Literal["add", "remove"]


class LLMResponse(BaseModel):
    """Structured response the LLM must return."""

    message: str = Field(description="Conversational response shown to the user")
    trades: list[TradeRequest] = Field(
        default_factory=list, description="Trades to execute immediately (empty if none)"
    )
    watchlist_changes: list[WatchlistChangeRequest] = Field(
        default_factory=list, description="Watchlist changes to apply (empty if none)"
    )
