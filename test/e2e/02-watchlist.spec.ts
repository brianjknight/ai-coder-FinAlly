import { test, expect } from "@playwright/test";
import { ensureNotInWatchlist, getWatchlist, openApp, parseMoney } from "./helpers";

const TICKER = "PYPL";

test.describe("Watchlist management", () => {
  test.beforeEach(async ({ request }) => {
    await ensureNotInWatchlist(request, TICKER);
  });

  test.afterAll(async ({ request }) => {
    await ensureNotInWatchlist(request, TICKER);
  });

  test("add and remove a ticker via the UI", async ({ page, request }) => {
    await openApp(page);
    await expect(page.getByTestId(`watchlist-row-${TICKER}`)).toHaveCount(0);

    // Lower-case input should be normalised to upper-case.
    await page.getByTestId("watchlist-add-input").fill(TICKER.toLowerCase());
    await page.getByTestId("watchlist-add-button").click();

    const row = page.getByTestId(`watchlist-row-${TICKER}`);
    await expect(row).toBeVisible();
    await expect.poll(() => getWatchlist(request)).toContain(TICKER);

    // The newly added ticker starts receiving prices from the stream.
    await expect
      .poll(async () => parseMoney(await page.getByTestId(`watchlist-price-${TICKER}`).textContent()), {
        timeout: 15_000,
      })
      .toBeGreaterThan(0);

    await page.getByTestId(`watchlist-remove-${TICKER}`).click();
    await expect(row).toHaveCount(0);
    await expect.poll(() => getWatchlist(request)).not.toContain(TICKER);
  });

  test("watchlist changes persist across a page reload", async ({ page, request }) => {
    await openApp(page);
    await page.getByTestId("watchlist-add-input").fill(TICKER);
    await page.getByTestId("watchlist-add-button").click();
    await expect(page.getByTestId(`watchlist-row-${TICKER}`)).toBeVisible();

    await page.reload();
    await expect(page.getByTestId(`watchlist-row-${TICKER}`)).toBeVisible();

    await page.getByTestId(`watchlist-remove-${TICKER}`).click();
    await expect(page.getByTestId(`watchlist-row-${TICKER}`)).toHaveCount(0);

    await page.reload();
    await expect(page.getByTestId("watchlist")).toBeVisible();
    await expect(page.getByTestId(`watchlist-row-${TICKER}`)).toHaveCount(0);
    await expect.poll(() => getWatchlist(request)).not.toContain(TICKER);
  });
});
