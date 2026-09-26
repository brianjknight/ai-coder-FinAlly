import { test, expect, Page } from "@playwright/test";
import { flattenPosition, getPortfolio, getPosition, moneyOf, openApp, waitForPrice } from "./helpers";

const TICKER = "JPM";

async function submitTrade(page: Page, ticker: string, quantity: number, side: "buy" | "sell") {
  await page.getByTestId("trade-ticker-input").fill(ticker);
  await page.getByTestId("trade-quantity-input").fill(String(quantity));
  await page.getByTestId(side === "buy" ? "trade-buy-button" : "trade-sell-button").click();
}

test.describe("Trading", () => {
  test.beforeEach(async ({ request }) => {
    await waitForPrice(request, TICKER);
    await flattenPosition(request, TICKER);
  });

  test("buy shares: cash decreases and a position row appears", async ({ page, request }) => {
    await openApp(page);
    const cashEl = page.getByTestId("header-cash");
    const before = await getPortfolio(request);
    await expect.poll(() => moneyOf(cashEl)).toBeCloseTo(before.cash_balance, 1);
    await expect(page.getByTestId(`position-row-${TICKER}`)).toHaveCount(0);

    await submitTrade(page, TICKER, 2, "buy");

    await expect(page.getByTestId("positions-table")).toBeVisible();
    await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();
    await expect.poll(() => moneyOf(cashEl)).toBeLessThan(before.cash_balance - 1);

    const pos = await getPosition(request, TICKER);
    expect(pos?.quantity).toBe(2);
    const after = await getPortfolio(request);
    // Cash drops by roughly quantity * fill price.
    expect(before.cash_balance - after.cash_balance).toBeCloseTo(2 * pos!.avg_cost, 1);
  });

  test("sell shares: cash increases, position updates then disappears", async ({ page, request }) => {
    // Seed a 2-share position through the API.
    const res = await request.post("/api/portfolio/trade", { data: { ticker: TICKER, side: "buy", quantity: 2 } });
    expect(res.status()).toBe(200);

    await openApp(page);
    const cashEl = page.getByTestId("header-cash");
    const row = page.getByTestId(`position-row-${TICKER}`);
    await expect(row).toBeVisible();

    const before = await getPortfolio(request);
    await expect.poll(() => moneyOf(cashEl)).toBeCloseTo(before.cash_balance, 1);

    // Partial sell -> position remains with 1 share.
    await submitTrade(page, TICKER, 1, "sell");
    await expect.poll(() => moneyOf(cashEl)).toBeGreaterThan(before.cash_balance + 1);
    await expect.poll(async () => (await getPosition(request, TICKER))?.quantity).toBe(1);
    await expect(row).toBeVisible();

    // Sell the rest -> position row disappears.
    const mid = (await getPortfolio(request)).cash_balance;
    await submitTrade(page, TICKER, 1, "sell");
    await expect(row).toHaveCount(0);
    await expect.poll(() => moneyOf(cashEl)).toBeGreaterThan(mid + 1);
    expect(await getPosition(request, TICKER)).toBeUndefined();
  });

  test("selling more than owned shows an error and changes nothing", async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);

    await submitTrade(page, TICKER, 5, "sell");
    await expect(page.getByTestId("trade-error")).toBeVisible();
    await expect(page.getByTestId("trade-error")).not.toBeEmpty();

    const after = await getPortfolio(request);
    expect(after.cash_balance).toBeCloseTo(before.cash_balance, 2);
    expect(await getPosition(request, TICKER)).toBeUndefined();
  });

  test("buying with insufficient cash shows an error", async ({ page, request }) => {
    await openApp(page);
    const before = await getPortfolio(request);

    await submitTrade(page, TICKER, 10_000_000, "buy");
    await expect(page.getByTestId("trade-error")).toBeVisible();
    await expect(page.getByTestId("trade-error")).not.toBeEmpty();

    const after = await getPortfolio(request);
    expect(after.cash_balance).toBeCloseTo(before.cash_balance, 2);
  });
});
