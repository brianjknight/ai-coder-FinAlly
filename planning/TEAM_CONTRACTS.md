# FinAlly — Team Contracts

Shared contract for the agent team. `PLAN.md` is the spec; this file pins down the
interfaces between team members so everyone can work in parallel. If you need to
change a contract, edit this file AND message the affected teammates.

## Team & Ownership

| Agent name | Role | Owns (only this agent edits these) |
|---|---|---|
| `db-engineer` | Database | `backend/app/db/**`, `backend/tests/db/**` |
| `backend-engineer` | Backend API | `backend/app/main.py`, `backend/app/api/**`, `backend/app/portfolio/**`, `backend/tests/api/**`, `backend/tests/portfolio/**`, `backend/pyproject.toml` + `uv.lock` (others ask it to add deps) |
| `llm-engineer` | LLM | `backend/app/llm/**`, `backend/tests/llm/**` |
| `frontend-engineer` | Frontend | `frontend/**` |
| `devops-engineer` | Docker/scripts | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `scripts/**`, `.env.example`, `.gitignore`, `db/.gitkeep` |
| `integration-tester` | E2E | `test/**` |

`backend/app/market/**` is complete — do not modify it without a very good reason (backend-engineer owns any needed change).

Do not commit to git; the lead handles commits.

## Backend layout

```
backend/app/
  main.py            # FastAPI app, lifespan, routers, static files  (backend-engineer)
  market/            # DONE
  db/                # connection, schema.sql, init/seed, repository functions (db-engineer)
  portfolio/         # trade execution + valuation service (backend-engineer)
  api/               # routers: portfolio, watchlist, chat, health (backend-engineer)
  llm/               # prompt, schema, LiteLLM call, mock mode (llm-engineer)
```

Run: `cd backend && uv run uvicorn app.main:app --port 8000`.

## Environment

- `DB_PATH` env var, default: `<repo_root>/db/finally.db` (in Docker: `/app/db/finally.db`, set via `DB_PATH=/app/db/finally.db`).
- `STATIC_DIR` env var, default `backend/static` (in Docker: `/app/static`). If the dir doesn't exist, skip static mounting.
- `.env` loaded from repo root with `python-dotenv` (`load_dotenv` searching upward) — harmless in Docker where `--env-file` is used.
- `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` per PLAN.md §5.

## DB module API (`app.db`) — db-engineer

Plain `sqlite3`, synchronous, one connection per call (or per-call context manager). Schema per PLAN.md §7 in `app/db/schema.sql`. Timestamps are ISO-8601 UTC strings. `user_id` defaults to `"default"` everywhere.

```python
init_db(db_path: str | None = None) -> None     # idempotent: create tables + seed if empty
get_connection() -> sqlite3.Connection          # row_factory = sqlite3.Row

get_cash_balance(user_id="default") -> float
set_cash_balance(cash: float, user_id="default") -> None

get_watchlist(user_id="default") -> list[str]              # tickers, in added order
add_watchlist_ticker(ticker, user_id="default") -> bool    # False if already present
remove_watchlist_ticker(ticker, user_id="default") -> bool # False if not present

get_positions(user_id="default") -> list[dict]   # {ticker, quantity, avg_cost, updated_at}
get_position(ticker, user_id="default") -> dict | None
upsert_position(ticker, quantity, avg_cost, user_id="default") -> None  # quantity==0 deletes the row

record_trade(ticker, side, quantity, price, user_id="default") -> dict
get_trades(user_id="default", limit=100) -> list[dict]

record_snapshot(total_value, user_id="default") -> None
get_snapshots(user_id="default", limit=1000) -> list[dict]   # {total_value, recorded_at}, oldest first

add_chat_message(role, content, actions: dict | None = None, user_id="default") -> dict
get_chat_history(user_id="default", limit=20) -> list[dict]  # {id, role, content, actions (parsed), created_at}, oldest first

execute_trade_atomic(ticker, side, quantity, price, new_cash, new_quantity, new_avg_cost,
                     user_id="default") -> dict
    # sets cash, upserts position (new_quantity==0 deletes), inserts trade -- ONE transaction.
    # No validation (caller validates). Returns trade dict {id, ticker, side, quantity, price, executed_at}.
```

Notes: `init_db(path)` makes `path` the active DB for all later calls (tests: `init_db(str(tmp_path / "t.db"))`).
Without it, the DB is lazily initialized on first `get_connection()` using `DB_PATH` / default.
Seeding happens only when the default user row is created (an emptied watchlist is not re-seeded).
`get_trades` returns most recent first. `get_snapshots`/`get_chat_history` return the most recent `limit`, oldest first.
Also exported: `get_db_path()`, `DEFAULT_WATCHLIST`, `DEFAULT_CASH_BALANCE`, `DEFAULT_USER_ID`.

## Portfolio service (`app.portfolio`) — backend-engineer

Used by both the REST API and the LLM module:

```python
class TradeError(Exception): ...   # message is user-facing ("Insufficient cash", ...)

execute_trade(ticker: str, side: str, quantity: float, price_cache) -> dict
    # validates (qty > 0, side in buy/sell, price available, cash / shares sufficient),
    # executes atomically, records a snapshot, returns the trade dict. Raises TradeError.

get_portfolio(price_cache) -> dict   # shape = GET /api/portfolio response
```

Watchlist changes must also call `source.add_ticker()` / `source.remove_ticker()` on the market data source (don't remove from the source if a position is still held). Provide `add_to_watchlist(ticker, source)` / `remove_from_watchlist(ticker, source)` helpers in `app.portfolio` for the LLM module to reuse.
These helpers are **async** (`await` them); they return the normalized ticker and raise
`WatchlistError(message, kind)` with `kind` in `invalid | exists | not_found` on failure.
Also exported: `normalize_ticker(t) -> str | None`, `record_portfolio_snapshot(price_cache) -> float`.

Background task: record a portfolio snapshot every 30s (in `main.py` lifespan).

## REST API (JSON) — backend-engineer

All errors: HTTP 4xx with `{"detail": "<message>"}` (FastAPI default).

`GET /api/health` → `{"status": "ok"}`

`GET /api/portfolio` →
```json
{
  "cash_balance": 8123.45,
  "total_value": 10234.56,
  "positions_value": 2111.11,
  "unrealized_pnl": 34.56,
  "positions": [
    {"ticker": "AAPL", "quantity": 10, "avg_cost": 190.1, "current_price": 192.3,
     "market_value": 1923.0, "unrealized_pnl": 22.0, "pnl_percent": 1.157}
  ]
}
```

`POST /api/portfolio/trade` body `{"ticker": "AAPL", "quantity": 10, "side": "buy"}` →
200 `{"trade": {"id", "ticker", "side", "quantity", "price", "executed_at"}, "portfolio": <GET /api/portfolio shape>}`;
400 `{"detail": "Insufficient cash"}` etc. Tickers are upper-cased server side.

`GET /api/portfolio/history` → `{"snapshots": [{"total_value": 10000.0, "recorded_at": "2026-...Z"}]}`

`GET /api/watchlist` →
```json
{"tickers": [{"ticker": "AAPL", "price": 190.5, "previous_price": 190.2,
              "change": 0.3, "change_percent": 0.157, "direction": "up"}]}
```
(price fields `null` if no price yet.)

`POST /api/watchlist` body `{"ticker": "PYPL"}` → 201 `{"ticker": "PYPL"}`; 409 if already present; 400 if invalid (must match `^[A-Z.]{1,10}$` after upper-casing).

`DELETE /api/watchlist/{ticker}` → 200 `{"ticker": "PYPL"}`; 404 if not present.

`POST /api/chat` body `{"message": "Buy 5 AAPL"}` →
```json
{
  "message": "Done — bought 5 AAPL at $190.12.",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5, "status": "executed", "price": 190.12, "error": null}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add", "status": "executed", "error": null}]
}
```
`status` is `"executed"` or `"failed"` (with `error` text).

`GET /api/chat/history` → `{"messages": [{"id", "role", "content", "actions", "created_at"}]}` (extra endpoint so the chat panel can restore history on reload).

`GET /api/stream/prices` — existing SSE; each event is `data: {"AAPL": {ticker, price, previous_price, timestamp, change, change_percent, direction}, ...}`.

## LLM module (`app.llm`) — llm-engineer

```python
async def handle_chat(message: str, price_cache, source) -> dict   # returns the POST /api/chat response shape
```
- Builds context via `app.portfolio.get_portfolio` + `app.db` watchlist, loads history via `app.db.get_chat_history`, calls LiteLLM per the `cerebras-inference` skill (`.claude/skills/cerebras/SKILL.md`) with a Pydantic structured-output model, executes trades via `app.portfolio.execute_trade` and watchlist changes via the portfolio helpers, stores both user and assistant messages (assistant with `actions`).
- `completion` is sync — call it via `asyncio.to_thread`.
- `LLM_MOCK=true` → deterministic responses, no network. Mock rules (the E2E tests depend on these):
  - message contains `buy <qty> <TICKER>` (case-insensitive) → executes that buy
  - message contains `sell <qty> <TICKER>` → executes that sell
  - message contains `watch <TICKER>` / `add <TICKER>` → adds to watchlist
  - otherwise → `{"message": "Mock response: I received your message.", "trades": [], "watchlist_changes": []}`
- LLM errors / malformed JSON → graceful response message, never a 500.
- Backend-engineer's `api/chat.py` just calls `handle_chat`.

## Frontend — frontend-engineer

Next.js + TypeScript + Tailwind, `output: 'export'`, build output `frontend/out/`. All calls same-origin `/api/*`. For local dev, `next.config` `rewrites` are not available with export — use an env-guarded dev proxy or run the backend serving `frontend/out` copied to `backend/static`.

Required `data-testid`s (E2E tests depend on them):
- `connection-status` (attribute `data-status="connected|reconnecting|disconnected"`)
- `header-total-value`, `header-cash`
- `watchlist`, `watchlist-row-{TICKER}`, `watchlist-price-{TICKER}`, `watchlist-remove-{TICKER}`, `watchlist-add-input`, `watchlist-add-button`
- `main-chart`, `selected-ticker`
- `trade-ticker-input`, `trade-quantity-input`, `trade-buy-button`, `trade-sell-button`, `trade-error`
- `positions-table`, `position-row-{TICKER}`
- `heatmap`, `pnl-chart`
- `chat-panel`, `chat-input`, `chat-send-button`, `chat-message` (each message; add `data-role`), `chat-loading`, `chat-action` (inline trade/watchlist confirmations)

## Docker — devops-engineer

Multi-stage per PLAN.md §11. Frontend `out/` copied to `/app/static`. Env in container: `DB_PATH=/app/db/finally.db`, `STATIC_DIR=/app/static`. Volume `finally-data:/app/db`. Image/container name `finally`. Healthcheck on `/api/health`.

## E2E — integration-tester

`test/docker-compose.test.yml`: app (built from root Dockerfile, `LLM_MOCK=true`, tmpfs/fresh DB) + `mcr.microsoft.com/playwright` container running `test/e2e`. Also runnable locally against `http://localhost:8000` via `BASE_URL`. Scenarios per PLAN.md §12.
