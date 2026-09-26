import { APIRequestContext, Page, expect, Locator } from "@playwright/test";

export const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

/** True when the run is against a freshly-created DB (set in docker-compose.test.yml). */
export const FRESH_DB = process.env.FRESH_DB === "1" || process.env.FRESH_DB === "true";

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number | null;
  market_value: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  positions_value: number;
  unrealized_pnl: number;
  positions: Position[];
}

/** Parse "$10,234.56" / "10,234.56" / "-$1.2" into a number. */
export function parseMoney(text: string | null | undefined): number {
  if (!text) return NaN;
  const cleaned = text.replace(/[^0-9.\-]/g, "");
  return parseFloat(cleaned);
}

export async function moneyOf(locator: Locator): Promise<number> {
  return parseMoney(await locator.textContent());
}

export async function getPortfolio(request: APIRequestContext): Promise<Portfolio> {
  const res = await request.get("/api/portfolio");
  expect(res.status()).toBe(200);
  return (await res.json()) as Portfolio;
}

export async function getPosition(request: APIRequestContext, ticker: string): Promise<Position | undefined> {
  const p = await getPortfolio(request);
  return p.positions.find((x) => x.ticker === ticker);
}

export async function getWatchlist(request: APIRequestContext): Promise<string[]> {
  const res = await request.get("/api/watchlist");
  expect(res.status()).toBe(200);
  const body = await res.json();
  return body.tickers.map((t: { ticker: string }) => t.ticker);
}

export async function ensureNotInWatchlist(request: APIRequestContext, ticker: string) {
  const tickers = await getWatchlist(request);
  if (tickers.includes(ticker)) {
    const res = await request.delete(`/api/watchlist/${ticker}`);
    expect([200, 404]).toContain(res.status());
  }
}

export async function ensureInWatchlist(request: APIRequestContext, ticker: string) {
  const tickers = await getWatchlist(request);
  if (!tickers.includes(ticker)) {
    const res = await request.post("/api/watchlist", { data: { ticker } });
    expect([201, 409]).toContain(res.status());
  }
}

export async function trade(request: APIRequestContext, ticker: string, side: "buy" | "sell", quantity: number) {
  const res = await request.post("/api/portfolio/trade", { data: { ticker, side, quantity } });
  expect(res.status(), await res.text()).toBe(200);
  return res.json();
}

/** Close out any existing position in the ticker so tests start from a known state. */
export async function flattenPosition(request: APIRequestContext, ticker: string) {
  const pos = await getPosition(request, ticker);
  if (pos && pos.quantity > 0) {
    await trade(request, ticker, "sell", pos.quantity);
  }
}

/** Wait until the backend has a live price for the ticker (so trades can fill). */
export async function waitForPrice(request: APIRequestContext, ticker: string) {
  await expect
    .poll(
      async () => {
        const res = await request.get("/api/watchlist");
        const body = await res.json();
        const row = body.tickers.find((t: { ticker: string }) => t.ticker === ticker);
        return row?.price ?? null;
      },
      { timeout: 15_000, message: `waiting for a price for ${ticker}` },
    )
    .not.toBeNull();
}

/** Load the app and wait for the SSE connection to be established. */
export async function openApp(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected", { timeout: 20_000 });
}
