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
