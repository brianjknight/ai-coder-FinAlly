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
