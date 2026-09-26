import { test, expect, Page } from "@playwright/test";
import { openApp, parseMoney } from "./helpers";

const STREAM = "**/api/stream/prices**";

/**
 * Chromium's offline emulation does not tear down an already-open SSE response, so to
 * simulate the server dropping the stream we track EventSource instances and expose
 * `window.__sseDrop()`, which closes live streams and fires `error` on them (what the
 * browser does when it gives up on a connection). Reconnect attempts are blocked with
 * a route abort until the "network" comes back.
 */
async function instrumentEventSource(page: Page) {
  await page.addInitScript(() => {
    const Orig = window.EventSource;
    const live: EventSource[] = [];
    class TrackedEventSource extends Orig {
      constructor(url: string | URL, init?: EventSourceInit) {
        super(url, init);
        live.push(this);
      }
    }
    (window as any).EventSource = TrackedEventSource;
    (window as any).__sseDrop = () => {
      let n = 0;
      for (const es of live) {
        if (es.readyState !== Orig.CLOSED) {
          es.close();
          es.dispatchEvent(new Event("error"));
          n++;
        }
      }
      return n;
    };
  });
}

const readAllPrices = (page: Page) =>
  page
    .locator('[data-testid^="watchlist-price-"]')
    .allTextContents()
    .then((t) => t.join("|"));

test.describe("SSE resilience", () => {
  test("stream drop: indicator leaves 'connected', then reconnects and prices resume", async ({ page, context }) => {
    await instrumentEventSource(page);
    await openApp(page);
    const status = page.getByTestId("connection-status");
    await expect.poll(async () => parseMoney(await page.getByTestId("watchlist-price-AAPL").textContent())).toBeGreaterThan(0);

    // Network goes away: block new stream connections, then drop the live one.
    await page.route(STREAM, (route) => route.abort("internetdisconnected"));
    await context.setOffline(true);
    const dropped = await page.evaluate(() => (window as any).__sseDrop());
    expect(dropped).toBeGreaterThan(0);

    await expect(status).toHaveAttribute("data-status", /reconnecting|disconnected/, { timeout: 10_000 });
    // While offline, prices stop updating and the status stays not-connected.
    await page.waitForTimeout(3000);
    await expect(status).not.toHaveAttribute("data-status", "connected");

    // Network returns: the app should reconnect on its own.
    await context.setOffline(false);
    await page.unroute(STREAM);
    await expect(status).toHaveAttribute("data-status", "connected", { timeout: 30_000 });

    const snapshot = await readAllPrices(page);
    await expect.poll(() => readAllPrices(page), { timeout: 15_000 }).not.toBe(snapshot);
  });

  test("stream unavailable at load: shows not-connected, then connects once available", async ({ page }) => {
    await page.route(STREAM, (route) => route.abort("connectionrefused"));
    await page.goto("/");
    const status = page.getByTestId("connection-status");
    await expect(status).toBeVisible();
    await page.waitForTimeout(3000);
    await expect(status).toHaveAttribute("data-status", /reconnecting|disconnected/);

    await page.unroute(STREAM);
    await expect(status).toHaveAttribute("data-status", "connected", { timeout: 30_000 });
    await expect.poll(async () => parseMoney(await page.getByTestId("watchlist-price-AAPL").textContent()), { timeout: 15_000 }).toBeGreaterThan(0);
  });
});
