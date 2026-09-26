<<<<<<< HEAD
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
=======
"""Fixtures for LLM service tests."""

import pytest

from app.db import init_db
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource


class MockMarketDataSource(MarketDataSource):
    """Minimal mock market data source for testing."""

    def __init__(self):
        self.added_tickers: list[str] = []
        self.removed_tickers: list[str] = []

    async def start(self, tickers: list[str]) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def add_ticker(self, ticker: str) -> None:
        self.added_tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed_tickers.append(ticker)

    def get_tickers(self) -> list[str]:
        return []


@pytest.fixture
async def db(tmp_path):
    """Create an isolated database per test."""
    db_path = str(tmp_path / "test.db")
    conn = await init_db(db_path)
    yield conn
    await conn.close()
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde


@pytest.fixture
def price_cache():
<<<<<<< HEAD
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.update("MSFT", 400.0)
=======
    """PriceCache with known prices for deterministic testing."""
    cache = PriceCache()
    cache.update("AAPL", 150.00)
    cache.update("GOOGL", 175.00)
    cache.update("MSFT", 400.00)
    cache.update("PYPL", 80.00)
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
    return cache


@pytest.fixture
<<<<<<< HEAD
def source():
    return FakeSource()


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.fixture
def live_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
=======
def market_source():
    """Mock market data source that tracks add/remove calls."""
    return MockMarketDataSource()
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
