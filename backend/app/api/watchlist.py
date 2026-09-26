"""Watchlist endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db
from app.market import MarketDataSource, PriceCache
from app.portfolio import WatchlistError, add_to_watchlist, remove_from_watchlist

from .deps import get_price_cache, get_source

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

_STATUS = {"invalid": 400, "exists": 409, "not_found": 404}


class AddTickerRequest(BaseModel):
    ticker: str


def _entry(ticker: str, cache: PriceCache) -> dict:
    update = cache.get(ticker)
    if update is None:
        return {
            "ticker": ticker,
            "price": None,
            "previous_price": None,
            "change": None,
            "change_percent": None,
            "direction": None,
        }
    return {
        "ticker": ticker,
        "price": update.price,
        "previous_price": update.previous_price,
        "change": update.change,
        "change_percent": update.change_percent,
        "direction": update.direction,
    }


@router.get("")
def read_watchlist(cache: PriceCache = Depends(get_price_cache)) -> dict:
    return {"tickers": [_entry(t, cache) for t in db.get_watchlist()]}


@router.post("", status_code=201)
async def add_ticker(
    req: AddTickerRequest, source: MarketDataSource | None = Depends(get_source)
) -> dict:
    try:
        ticker = await add_to_watchlist(req.ticker, source)
    except WatchlistError as e:
        raise HTTPException(status_code=_STATUS[e.kind], detail=str(e)) from None
    return {"ticker": ticker}


@router.delete("/{ticker}")
async def remove_ticker(
    ticker: str, source: MarketDataSource | None = Depends(get_source)
) -> dict:
    try:
        removed = await remove_from_watchlist(ticker, source)
    except WatchlistError as e:
        status = 404 if e.kind == "invalid" else _STATUS[e.kind]
        raise HTTPException(status_code=status, detail=str(e)) from None
    return {"ticker": removed}
