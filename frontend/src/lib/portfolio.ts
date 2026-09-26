import type { Portfolio, Position, PriceMap } from "./types";

/** Reprice positions with the latest streamed prices (falls back to the server's price). */
export function livePositions(portfolio: Portfolio | null, prices: PriceMap): Position[] {
  if (!portfolio) return [];
  return portfolio.positions.map((p) => {
    const live = prices[p.ticker]?.price;
    const price = live ?? p.current_price ?? p.avg_cost;
    const market_value = p.quantity * price;
    const cost = p.quantity * p.avg_cost;
    const unrealized_pnl = market_value - cost;
    const pnl_percent = cost > 0 ? (unrealized_pnl / cost) * 100 : 0;
    return { ...p, current_price: price, market_value, unrealized_pnl, pnl_percent };
  });
}

export interface PortfolioTotals {
  cash: number;
  positionsValue: number;
  totalValue: number;
  unrealizedPnl: number;
}

export function portfolioTotals(portfolio: Portfolio | null, positions: Position[]): PortfolioTotals {
  const cash = portfolio?.cash_balance ?? 0;
  const positionsValue = positions.reduce((s, p) => s + p.market_value, 0);
  const unrealizedPnl = positions.reduce((s, p) => s + p.unrealized_pnl, 0);
  return { cash, positionsValue, totalValue: cash + positionsValue, unrealizedPnl };
}
