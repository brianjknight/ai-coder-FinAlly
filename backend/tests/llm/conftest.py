"""Fixtures for app.llm tests: fresh SQLite DB, real PriceCache and portfolio, fake source."""

import pytest

from app.db import connection
from app.market.cache import PriceCache


class FakeSource:
    """Records add/remove calls; async like the real MarketDataSource."""

    def __init__(self):
        self.added: list[str] = []
        self.removed: list[str] = []

    async def add_ticker(self, ticker):
        self.added.append(ticker)

    async def remove_ticker(self, ticker):
        self.removed.append(ticker)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    connection.reset_for_tests()
    connection.init_db(str(tmp_path / "finally.db"))
    yield
    connection.reset_for_tests()


@pytest.fixture
def price_cache():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.update("MSFT", 400.0)
    return cache


@pytest.fixture
def source():
    return FakeSource()


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.fixture
def live_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
