<<<<<<< HEAD
"""Fixtures for app.db tests: each test gets a fresh SQLite file under tmp_path."""

import pytest

from app.db import connection


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    connection.reset_for_tests()
    path = tmp_path / "sub" / "finally.db"
    connection.init_db(str(path))
    yield path
    connection.reset_for_tests()
=======
"""Fixtures for database tests."""

import pytest

from app.db import init_db


@pytest.fixture
async def db(tmp_path):
    """Create an isolated database per test."""
    db_path = str(tmp_path / "test.db")
    conn = await init_db(db_path)
    yield conn
    await conn.close()


@pytest.fixture
def db_path(tmp_path):
    """Return a tmp path string for tests that manage their own connections."""
    return str(tmp_path / "test.db")
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
