<<<<<<< HEAD
"""System prompt and portfolio-context construction."""

from __future__ import annotations

import json

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant inside a simulated trading workstation.
The user trades a simulated portfolio with virtual money (market orders only, instant fill at the
current price, no fees). You can:
- Analyze portfolio composition, risk concentration, and P&L.
- Suggest trades with brief reasoning.
- Execute trades when the user asks or agrees, by listing them in "trades".
- Manage the watchlist proactively, by listing changes in "watchlist_changes".

Rules:
- Be concise and data-driven. Reference actual numbers from the portfolio context.
- Only include a trade when the user asked for it or clearly agreed to it. Never invent trades.
- Buys need enough cash (quantity * current price <= cash); sells need enough shares held.
  If a request is not feasible, explain why instead of submitting it.
- Quantities must be positive; fractional shares are allowed. Tickers are upper-case symbols.
- Trades and watchlist changes you list are executed automatically right after you respond;
  describe them in "message" as being executed (e.g. "Buying 5 AAPL at ~$190").
- Always respond with valid JSON matching the required schema: "message" (string),
  "trades" (array, possibly empty), "watchlist_changes" (array, possibly empty)."""


def _round(value, digits: int = 2):
    return round(value, digits) if isinstance(value, (int, float)) else value


def build_context(portfolio: dict, watchlist: list[str], price_cache) -> str:
    """Render the user's live portfolio + watchlist as a compact JSON context block."""
    positions = [
        {
            "ticker": p.get("ticker"),
            "quantity": p.get("quantity"),
            "avg_cost": _round(p.get("avg_cost")),
            "current_price": _round(p.get("current_price")),
            "market_value": _round(p.get("market_value")),
            "unrealized_pnl": _round(p.get("unrealized_pnl")),
            "pnl_percent": _round(p.get("pnl_percent")),
        }
        for p in portfolio.get("positions", [])
    ]
    watch = []
    for ticker in watchlist:
        upd = price_cache.get(ticker) if price_cache is not None else None
        watch.append(
            {
                "ticker": ticker,
                "price": upd.price if upd else None,
                "change_percent": _round(upd.change_percent, 3) if upd else None,
            }
        )
    context = {
        "cash_balance": _round(portfolio.get("cash_balance")),
        "total_value": _round(portfolio.get("total_value")),
        "positions_value": _round(portfolio.get("positions_value")),
        "unrealized_pnl": _round(portfolio.get("unrealized_pnl")),
        "positions": positions,
        "watchlist": watch,
    }
    return "Current portfolio context (live):\n" + json.dumps(context)


def build_messages(context: str, history: list[dict], user_message: str) -> list[dict]:
    """System prompt + context + recent history + the new user message."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context},
    ]
    for msg in history:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages
=======
"""System prompt builder for LLM chat context."""


def build_system_prompt(portfolio: dict, watchlist_prices: list[dict]) -> str:
    """Build a system prompt with live portfolio state and watchlist prices.

    Args:
        portfolio: Dict from get_portfolio() with cash_balance, positions, total_value.
        watchlist_prices: List of dicts with ticker and price from the watchlist.
    """
    positions_text = ""
    for p in portfolio["positions"]:
        positions_text += (
            f"  {p['ticker']}: {p['quantity']} shares, "
            f"avg cost ${p['avg_cost']:.2f}, "
            f"current ${p['current_price']:.2f}, "
            f"P&L ${p['unrealized_pnl']:.2f} ({p['unrealized_pnl_percent']:+.1f}%)\n"
        )

    watchlist_text = ""
    for w in watchlist_prices:
        watchlist_text += f"  {w['ticker']}: ${w['price']:.2f}\n"

    return f"""You are FinAlly, an AI trading assistant for a simulated portfolio.
You analyze positions, suggest trades, execute trades, and manage the watchlist.
Be concise and data-driven. Always respond with valid JSON.

Current portfolio:
  Cash: ${portfolio['cash_balance']:.2f}
  Total value: ${portfolio['total_value']:.2f}
  Positions:
{positions_text or '  (none)'}
Watchlist prices:
{watchlist_text or '  (none)'}
You MUST respond with JSON matching this exact schema:
{{
  "message": "your response text",
  "trades": [{{"ticker": "AAPL", "side": "buy", "quantity": 10}}],
  "watchlist_changes": [{{"ticker": "PYPL", "action": "add"}}]
}}
trades and watchlist_changes are optional arrays (use empty arrays if no actions needed)."""
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
