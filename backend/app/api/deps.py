"""Shared request helpers: access the app-wide price cache and market data source."""

from fastapi import Request

from app.market import MarketDataSource, PriceCache


def get_price_cache(request: Request) -> PriceCache:
    return request.app.state.price_cache


def get_source(request: Request) -> MarketDataSource | None:
    return getattr(request.app.state, "market_source", None)
