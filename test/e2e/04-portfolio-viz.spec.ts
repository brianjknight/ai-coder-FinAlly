import { test, expect } from "@playwright/test";
import { getPosition, openApp, trade, waitForPrice } from "./helpers";

const TICKER = "MSFT";

test.describe("Portfolio visualisations", () => {
  test.beforeEach(async ({ request }) => {
    await waitForPrice(request, TICKER);
    // Make sure there's at least one position for the heatmap and a snapshot for the P&L chart.
    const pos = await getPosition(request, TICKER);
    if (!pos) await trade(request, TICKER, "buy", 1);
  });

  test("heatmap renders a cell for held positions", async ({ page }) => {
    await openApp(page);
    const heatmap = page.getByTestId("heatmap");
    await expect(heatmap).toBeVisible();
    await expect(heatmap).toContainText(TICKER);

    const box = await heatmap.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(50);
    expect(box?.height ?? 0).toBeGreaterThan(50);
  });

  test("P&L chart renders with snapshot data", async ({ page, request }) => {
    const res = await request.get("/api/portfolio/history");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.snapshots.length).toBeGreaterThan(0);

    await openApp(page);
    const chart = page.getByTestId("pnl-chart");
    await expect(chart).toBeVisible();
    // Chart library renders into a canvas (lightweight-charts) or svg (recharts).
    await expect(chart.locator("canvas, svg").first()).toBeVisible();

    const box = await chart.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(50);
    expect(box?.height ?? 0).toBeGreaterThan(50);
  });

  test("main chart renders for the selected ticker", async ({ page }) => {
    await openApp(page);
    await page.getByTestId(`watchlist-row-${TICKER}`).click();
    await expect(page.getByTestId("selected-ticker")).toContainText(TICKER);
    await expect(page.getByTestId("main-chart").locator("canvas, svg").first()).toBeVisible();
  });
});
