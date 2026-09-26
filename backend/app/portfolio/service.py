"""Trade execution, portfolio valuation and watchlist management."""

from __future__ import annotations

import logging
import re
import threading
from typing import Any

from app import db
from app.market import MarketDataSource, PriceCache

logger = logging.getLogger(__name__)

TICKER_PATTERN = re.compile(r"^[A-Z.]{1,10}$")

# Tolerance for float comparisons (e.g. selling "all" of a fractional position).
_QTY_EPSILON = 1e-6
_CASH_EPSILON = 1e-6

# Serialize trades so validation + execution can't interleave between requests.
_trade_lock = threading.Lock()


class TradeError(Exception):
    """A trade was rejected. The message is user-facing."""


class WatchlistError(Exception):
    """A watchlist change was rejected. ``kind`` is 'invalid', 'exists' or 'not_found'."""

    def __init__(self, message: str, kind: str) -> None:
        super().__init__(message)
        self.kind = kind


def normalize_ticker(ticker: Any) -> str | None:
    """Upper-case and strip a ticker; return None if it is not a valid symbol."""
    if not isinstance(ticker, str):
        return None
    t = ticker.strip().upper()
    return t if TICKER_PATTERN.match(t) else None


# --- valuation -----------------------------------------------------------------


def get_portfolio(price_cache: PriceCache) -> dict:
    """Current portfolio (shape of GET /api/portfolio).

    Positions without a live price are valued at their average cost.
    """
    cash = db.get_cash_balance()
    positions_out: list[dict] = []
    positions_value = 0.0
    total_cost = 0.0

    for pos in db.get_positions():
        qty = pos["quantity"]
        avg_cost = pos["avg_cost"]
        price = price_cache.get_price(pos["ticker"])
        current = price if price is not None else avg_cost
        market_value = qty * current
        cost_basis = qty * avg_cost
        pnl = market_value - cost_basis
        pnl_pct = (current - avg_cost) / avg_cost * 100 if avg_cost else 0.0
        positions_value += market_value
        total_cost += cost_basis
        positions_out.append(
            {
                "ticker": pos["ticker"],
                "quantity": qty,
                "avg_cost": round(avg_cost, 4),
                "current_price": round(current, 4),
                "market_value": round(market_value, 2),
                "unrealized_pnl": round(pnl, 2),
                "pnl_percent": round(pnl_pct, 3),
            }
        )

    return {
        "cash_balance": round(cash, 2),
        "total_value": round(cash + positions_value, 2),
        "positions_value": round(positions_value, 2),
        "unrealized_pnl": round(positions_value - total_cost, 2),
        "positions": positions_out,
    }


def record_portfolio_snapshot(price_cache: PriceCache) -> float:
    """Record the current total portfolio value. Returns the recorded value."""
    total = get_portfolio(price_cache)["total_value"]
    db.record_snapshot(total)
    return total


# --- trading -------------------------------------------------------------------


def execute_trade(ticker: str, side: str, quantity: float, price_cache: PriceCache) -> dict:
    """Validate and execute a market order at the current cached price.

    Returns the trade dict ``{id, ticker, side, quantity, price, executed_at}``.
    Raises TradeError with a user-facing message on any validation failure.
    """
    symbol = normalize_ticker(ticker)
    if symbol is None:
        raise TradeError(f"Invalid ticker: {ticker!r}")

    side_norm = side.strip().lower() if isinstance(side, str) else ""
    if side_norm not in ("buy", "sell"):
        raise TradeError("Side must be 'buy' or 'sell'")

    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise TradeError("Quantity must be a number") from None
    if not qty > 0 or qty == float("inf"):
        raise TradeError("Quantity must be greater than 0")

    price = price_cache.get_price(symbol)
    if price is None or price <= 0:
        raise TradeError(f"No price available for {symbol}")

    with _trade_lock:
        cash = db.get_cash_balance()
        pos = db.get_position(symbol)
        held = pos["quantity"] if pos else 0.0
        avg_cost = pos["avg_cost"] if pos else 0.0

        if side_norm == "buy":
            cost = qty * price
            if cost > cash + _CASH_EPSILON:
                raise TradeError(
                    f"Insufficient cash: need ${cost:,.2f}, have ${cash:,.2f}"
                )
            new_cash = max(cash - cost, 0.0)
            new_qty = held + qty
            new_avg = (held * avg_cost + qty * price) / new_qty
        else:
            if qty > held + _QTY_EPSILON:
                raise TradeError(
                    f"Insufficient shares: trying to sell {qty:g} {symbol}, own {held:g}"
                )
            if abs(held - qty) <= _QTY_EPSILON:
                qty = held  # sell the whole position exactly
                new_qty = 0.0
            else:
                new_qty = held - qty
            new_cash = cash + qty * price
            new_avg = avg_cost

        trade = db.execute_trade_atomic(
            ticker=symbol,
            side=side_norm,
            quantity=qty,
            price=price,
            new_cash=new_cash,
            new_quantity=new_qty,
            new_avg_cost=new_avg,
        )

    try:
        record_portfolio_snapshot(price_cache)
    except Exception:  # snapshot failure must not fail an executed trade
        logger.exception("Failed to record post-trade snapshot")

    logger.info("Executed %s %g %s @ %.2f", side_norm, qty, symbol, price)
    return trade


# --- watchlist -----------------------------------------------------------------


async def add_to_watchlist(ticker: str, source: MarketDataSource | None) -> str:
    """Add a ticker to the watchlist and start tracking it. Returns the normalized ticker.

    Raises WatchlistError (kind 'invalid' or 'exists').
    """
    symbol = normalize_ticker(ticker)
    if symbol is None:
        raise WatchlistError(f"Invalid ticker: {ticker!r}", "invalid")
    if not db.add_watchlist_ticker(symbol):
        raise WatchlistError(f"{symbol} is already in the watchlist", "exists")
    if source is not None:
        await source.add_ticker(symbol)
    return symbol


async def remove_from_watchlist(ticker: str, source: MarketDataSource | None) -> str:
    """Remove a ticker from the watchlist. Returns the normalized ticker.

    The market data source keeps tracking the ticker while a position is held.
    Raises WatchlistError (kind 'invalid' or 'not_found').
    """
    symbol = normalize_ticker(ticker)
    if symbol is None:
        raise WatchlistError(f"Invalid ticker: {ticker!r}", "invalid")
    if not db.remove_watchlist_ticker(symbol):
        raise WatchlistError(f"{symbol} is not in the watchlist", "not_found")
    if source is not None and db.get_position(symbol) is None:
        await source.remove_ticker(symbol)
    return symbol
