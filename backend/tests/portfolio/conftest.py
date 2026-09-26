<<<<<<< HEAD
"""Fixtures for portfolio service tests: fresh temp DB and a hand-fed PriceCache."""

import pytest

from app.db import connection
from app.market import PriceCache


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    connection.reset_for_tests()
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    connection.init_db()
    yield
    connection.reset_for_tests()


@pytest.fixture
def cache(fresh_db):
    c = PriceCache()
    c.update("AAPL", 100.0)
    c.update("MSFT", 200.0)
    return c


class FakeSource:
    """Records add/remove calls instead of producing prices."""

    def __init__(self):
        self.added: list[str] = []
        self.removed: list[str] = []

    async def add_ticker(self, ticker):
        self.added.append(ticker)

    async def remove_ticker(self, ticker):
        self.removed.append(ticker)


@pytest.fixture
def source():
    return FakeSource()
=======
"""Fixtures for portfolio service tests."""

import pytest

from app.db import init_db
from app.market.cache import PriceCache


@pytest.fixture
async def db(tmp_path):
    """Create an isolated database per test."""
    db_path = str(tmp_path / "test.db")
    conn = await init_db(db_path)
    yield conn
    await conn.close()


@pytest.fixture
def price_cache():
    """PriceCache with known prices for deterministic testing."""
    cache = PriceCache()
    cache.update("AAPL", 150.00)
    cache.update("GOOGL", 175.00)
    cache.update("MSFT", 400.00)
    return cache
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
