"""Watchlist helper tests for app.portfolio."""

import pytest

from app import db
from app.portfolio import WatchlistError, add_to_watchlist, execute_trade, remove_from_watchlist


async def test_add_normalizes_and_tracks(fresh_db, source):
    assert await add_to_watchlist(" pypl ", source) == "PYPL"
    assert "PYPL" in db.get_watchlist()
    assert source.added == ["PYPL"]


async def test_add_duplicate(fresh_db, source):
    with pytest.raises(WatchlistError) as ei:
        await add_to_watchlist("AAPL", source)
    assert ei.value.kind == "exists"
    assert source.added == []


@pytest.mark.parametrize("bad", ["", "123", "ABCDEFGHIJK", "A B"])
async def test_add_invalid(fresh_db, source, bad):
    with pytest.raises(WatchlistError) as ei:
        await add_to_watchlist(bad, source)
    assert ei.value.kind == "invalid"


async def test_remove(fresh_db, source):
    assert await remove_from_watchlist("aapl", source) == "AAPL"
    assert "AAPL" not in db.get_watchlist()
    assert source.removed == ["AAPL"]


async def test_remove_missing(fresh_db, source):
    with pytest.raises(WatchlistError) as ei:
        await remove_from_watchlist("ZZZ", source)
    assert ei.value.kind == "not_found"


async def test_remove_keeps_tracking_held_position(cache, source):
    execute_trade("AAPL", "buy", 1, cache)
    await remove_from_watchlist("AAPL", source)
    assert "AAPL" not in db.get_watchlist()
    assert source.removed == []


async def test_works_without_source(fresh_db):
    assert await add_to_watchlist("PYPL", None) == "PYPL"
    assert await remove_from_watchlist("PYPL", None) == "PYPL"
