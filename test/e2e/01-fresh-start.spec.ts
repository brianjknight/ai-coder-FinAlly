import { test, expect } from "@playwright/test";
import { DEFAULT_TICKERS, FRESH_DB, getPortfolio, moneyOf, openApp, parseMoney } from "./helpers";

test.describe("Fresh start", () => {
  test("shows default watchlist, cash, connection status and header values", async ({ page, request }) => {
    await openApp(page);

    await expect(page.getByTestId("watchlist")).toBeVisible();
    for (const t of DEFAULT_TICKERS) {
      await expect(page.getByTestId(`watchlist-row-${t}`), `watchlist row ${t}`).toBeVisible();
    }

    const portfolio = await getPortfolio(request);
    const cashEl = page.getByTestId("header-cash");
    await expect(cashEl).toBeVisible();
    await expect(page.getByTestId("header-total-value")).toBeVisible();

    if (FRESH_DB) {
      expect(portfolio.cash_balance).toBe(10000);
      expect(portfolio.positions).toHaveLength(0);
      await expect(cashEl).toContainText("10,000");
    }
    // Header cash must reflect the backend cash balance regardless of DB state.
    await expect.poll(() => moneyOf(cashEl)).toBeCloseTo(portfolio.cash_balance, 1);

    // Total value is a positive number (cash + positions).
    await expect
      .poll(async () => parseMoney(await page.getByTestId("header-total-value").textContent()))
      .toBeGreaterThan(0);
  });

  test("prices stream and change over time", async ({ page }) => {
    await openApp(page);

    const readPrices = async () => {
      const out: Record<string, string> = {};
      for (const t of DEFAULT_TICKERS) {
        out[t] = ((await page.getByTestId(`watchlist-price-${t}`).textContent()) || "").trim();
      }
      return out;
    };

    // Every default ticker gets a numeric price.
    await expect
      .poll(
        async () => Object.values(await readPrices()).every((p) => !isNaN(parseMoney(p)) && parseMoney(p) > 0),
        { timeout: 15_000 },
      )
      .toBe(true);

    const initial = await readPrices();
    // At least one price changes within a few seconds (simulator ticks every ~500ms).
    await expect
      .poll(
        async () => {
          const now = await readPrices();
          return DEFAULT_TICKERS.filter((t) => now[t] !== initial[t]).length;
        },
        { timeout: 15_000 },
      )
      .toBeGreaterThan(0);
  });

  test("clicking a watchlist ticker selects it in the main chart", async ({ page }) => {
    await openApp(page);
    await expect(page.getByTestId("main-chart")).toBeVisible();

    await page.getByTestId("watchlist-row-MSFT").click();
    await expect(page.getByTestId("selected-ticker")).toContainText("MSFT");

    await page.getByTestId("watchlist-row-NVDA").click();
    await expect(page.getByTestId("selected-ticker")).toContainText("NVDA");
  });
});
