"""Fixtures for API tests: a fresh app on a temp DB with a deterministic price source."""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.db import connection
from app.market import MarketDataSource

FIXED_PRICES = {
    "AAPL": 100.0, "GOOGL": 150.0, "MSFT": 200.0, "AMZN": 180.0, "TSLA": 250.0,
    "NVDA": 800.0, "META": 500.0, "JPM": 190.0, "V": 280.0, "NFLX": 600.0,
}


class FixedPriceSource(MarketDataSource):
    """Writes fixed prices to the cache; new tickers get $50."""

    def __init__(self, cache):
        self.cache = cache
        self.tickers: list[str] = []
        self.stopped = False

    async def start(self, tickers):
        for t in tickers:
            await self.add_ticker(t)

    async def stop(self):
        self.stopped = True

    async def add_ticker(self, ticker):
        if ticker not in self.tickers:
            self.tickers.append(ticker)
        self.cache.update(ticker, FIXED_PRICES.get(ticker, 50.0))

    async def remove_ticker(self, ticker):
        if ticker in self.tickers:
            self.tickers.remove(ticker)
        self.cache.remove(ticker)

    def get_tickers(self):
        return list(self.tickers)


@pytest.fixture
def app(tmp_path, monkeypatch):
    connection.reset_for_tests()
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-static"))
    monkeypatch.setattr(main, "create_market_data_source", FixedPriceSource)
    application = main.create_app()
    yield application
    connection.reset_for_tests()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c
