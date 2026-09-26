<<<<<<< HEAD
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
=======
"""Portfolio business logic: trade execution, portfolio queries, history."""

from datetime import datetime, timezone
from uuid import uuid4

import aiosqlite

from app.market.cache import PriceCache


async def execute_trade(
    db: aiosqlite.Connection,
    price_cache: PriceCache,
    ticker: str,
    side: str,
    quantity: float,
) -> dict:
    """Execute a market order (buy or sell) with atomic transaction.

    Returns dict with ticker, side, quantity, price, total.
    Raises ValueError for insufficient cash, insufficient shares, or missing price.
    """
    current_price = price_cache.get_price(ticker)
    if current_price is None:
        raise ValueError(f"No price available for {ticker}")

    cost = round(current_price * quantity, 2)
    now = datetime.now(timezone.utc).isoformat()

    try:
        await db.execute("BEGIN")

        if side == "buy":
            row = await db.execute_fetchall(
                "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
            )
            cash = row[0][0]
            if cash < cost:
                raise ValueError(
                    f"Insufficient cash: need ${cost:.2f}, have ${cash:.2f}"
                )

            await db.execute(
                "UPDATE users_profile SET cash_balance = cash_balance - ? WHERE id = ?",
                (cost, "default"),
            )

            await db.execute(
                """INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
                VALUES (?, 'default', ?, ?, ?, ?)
                ON CONFLICT(user_id, ticker) DO UPDATE SET
                    quantity = positions.quantity + excluded.quantity,
                    avg_cost = (positions.avg_cost * positions.quantity + excluded.avg_cost * excluded.quantity)
                              / (positions.quantity + excluded.quantity),
                    updated_at = excluded.updated_at""",
                (str(uuid4()), ticker, quantity, current_price, now),
            )

        else:  # sell
            row = await db.execute_fetchall(
                "SELECT quantity FROM positions WHERE user_id = ? AND ticker = ?",
                ("default", ticker),
            )
            if not row:
                raise ValueError(f"Insufficient shares: no position in {ticker}")

            owned_qty = row[0][0]
            if owned_qty < quantity:
                raise ValueError(
                    f"Insufficient shares: need {quantity}, have {owned_qty}"
                )

            await db.execute(
                "UPDATE users_profile SET cash_balance = cash_balance + ? WHERE id = ?",
                (cost, "default"),
            )

            new_qty = owned_qty - quantity
            if new_qty < 0.0001:
                await db.execute(
                    "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                    ("default", ticker),
                )
            else:
                await db.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                    (new_qty, now, "default", ticker),
                )

        # Record trade in append-only log
        await db.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid4()), "default", ticker, side, quantity, current_price, now),
        )

        await db.execute("COMMIT")

    except Exception:
        await db.execute("ROLLBACK")
        raise

    return {
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": current_price,
        "total": cost,
    }


async def get_portfolio(db: aiosqlite.Connection, price_cache: PriceCache) -> dict:
    """Get current portfolio state with live prices and P&L.

    Returns dict with cash_balance, positions list, and total_value.
    Falls back to avg_cost if price_cache has no current price for a ticker.
    """
    row = await db.execute_fetchall(
        "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
    )
    cash_balance = row[0][0]

    rows = await db.execute_fetchall(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?",
        ("default",),
    )

    positions = []
    total_market_value = 0.0

    for r in rows:
        ticker, qty, avg_cost = r[0], r[1], r[2]
        current_price = price_cache.get_price(ticker)
        if current_price is None:
            current_price = avg_cost

        market_value = round(current_price * qty, 2)
        cost_basis = round(avg_cost * qty, 2)
        unrealized_pnl = round(market_value - cost_basis, 2)
        unrealized_pnl_percent = round((unrealized_pnl / cost_basis) * 100, 2) if cost_basis else 0.0

        positions.append({
            "ticker": ticker,
            "quantity": qty,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_percent": unrealized_pnl_percent,
        })
        total_market_value += market_value

    return {
        "cash_balance": cash_balance,
        "positions": positions,
        "total_value": round(cash_balance + total_market_value, 2),
    }


async def get_portfolio_history(db: aiosqlite.Connection) -> dict:
    """Get portfolio value snapshots ordered chronologically.

    Returns dict with snapshots list (each: total_value, recorded_at).
    """
    rows = await db.execute_fetchall(
        "SELECT total_value, recorded_at FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at ASC",
        ("default",),
    )

    return {
        "snapshots": [
            {"total_value": r[0], "recorded_at": r[1]}
            for r in rows
        ],
    }
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
