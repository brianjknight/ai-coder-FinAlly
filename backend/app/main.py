"""FinAlly FastAPI application: API routes, SSE stream, background tasks, static frontend."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.api import chat_router, health_router, portfolio_router, watchlist_router
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.portfolio import record_portfolio_snapshot

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[1]
SNAPSHOT_INTERVAL_SECONDS = 30.0


def _load_env() -> None:
    """Load .env from the repo root (searching upward). Never overrides real env vars."""
    path = find_dotenv(usecwd=True) or str(_BACKEND_DIR.parent / ".env")
    if os.path.exists(path):
        load_dotenv(path, override=False)


async def _snapshot_loop(cache: PriceCache, interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(record_portfolio_snapshot, cache)
        except Exception:
            logger.exception("Periodic portfolio snapshot failed")


def _initial_tickers() -> list[str]:
    """Watchlist tickers plus any held-position tickers (so positions stay priced)."""
    tickers = list(db.get_watchlist())
    for pos in db.get_positions():
        if pos["ticker"] not in tickers:
            tickers.append(pos["ticker"])
    return tickers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    cache: PriceCache = app.state.price_cache
    source = create_market_data_source(cache)
    await source.start(_initial_tickers())
    app.state.market_source = source

    # Baseline snapshot so the P&L chart has a starting point.
    try:
        record_portfolio_snapshot(cache)
    except Exception:
        logger.exception("Initial portfolio snapshot failed")

    snapshot_task = asyncio.create_task(
        _snapshot_loop(cache, SNAPSHOT_INTERVAL_SECONDS), name="portfolio-snapshots"
    )
    logger.info("FinAlly started (db=%s)", db.get_db_path())
    try:
        yield
    finally:
        snapshot_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await snapshot_task
        await source.stop()
        logger.info("FinAlly stopped")


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Flatten pydantic errors to the contract's {"detail": "<message>"} shape."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()) if p != "body")
        parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
    return JSONResponse(status_code=422, content={"detail": "; ".join(parts) or "Invalid request"})


def create_app() -> FastAPI:
    _load_env()
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.state.price_cache = PriceCache()
    app.state.market_source = None
    app.add_exception_handler(RequestValidationError, _validation_error_handler)

    app.include_router(health_router)
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)
    app.include_router(chat_router)
    app.include_router(create_stream_router(app.state.price_cache))

    # Static frontend last so /api/* routes take precedence.
    static_dir = Path(os.environ.get("STATIC_DIR") or (_BACKEND_DIR / "static"))
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
        logger.info("Serving static frontend from %s", static_dir)
    else:
        logger.info("Static dir %s not found; frontend not served", static_dir)

    return app


app = create_app()
