<<<<<<< HEAD
"""Portfolio service: trade execution, valuation and watchlist helpers.

Shared by the REST API and the LLM module. See planning/TEAM_CONTRACTS.md.
"""

from .service import (
    TICKER_PATTERN,
    TradeError,
    WatchlistError,
    add_to_watchlist,
    execute_trade,
    get_portfolio,
    normalize_ticker,
    record_portfolio_snapshot,
    remove_from_watchlist,
)

__all__ = [
    "TICKER_PATTERN",
    "TradeError",
    "WatchlistError",
    "add_to_watchlist",
    "execute_trade",
    "get_portfolio",
    "normalize_ticker",
    "record_portfolio_snapshot",
    "remove_from_watchlist",
=======
"""Portfolio service layer for FinAlly.

Provides trade execution, portfolio querying, portfolio history retrieval,
and background snapshot recording.
"""

from .models import (
    PortfolioHistoryResponse,
    PortfolioResponse,
    PositionResponse,
    SnapshotResponse,
    TradeRequest,
    TradeResponse,
)
from .service import execute_trade, get_portfolio, get_portfolio_history
from .snapshots import record_snapshot, start_snapshot_task, stop_snapshot_task

__all__ = [
    "TradeRequest",
    "TradeResponse",
    "PositionResponse",
    "PortfolioResponse",
    "SnapshotResponse",
    "PortfolioHistoryResponse",
    "execute_trade",
    "get_portfolio",
    "get_portfolio_history",
    "record_snapshot",
    "start_snapshot_task",
    "stop_snapshot_task",
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
]
