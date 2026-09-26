"""Portfolio endpoints: current holdings, trade execution and value history."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db
from app.market import PriceCache
from app.portfolio import TradeError, execute_trade, get_portfolio

from .deps import get_price_cache

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    quantity: Any  # validated by the portfolio service for user-facing messages
    side: str


@router.get("")
def read_portfolio(cache: PriceCache = Depends(get_price_cache)) -> dict:
    return get_portfolio(cache)


@router.post("/trade")
def trade(req: TradeRequest, cache: PriceCache = Depends(get_price_cache)) -> dict:
    try:
        executed = execute_trade(req.ticker, req.side, req.quantity, cache)
    except TradeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return {"trade": executed, "portfolio": get_portfolio(cache)}


@router.get("/history")
def history() -> dict:
    return {"snapshots": db.get_snapshots()}
