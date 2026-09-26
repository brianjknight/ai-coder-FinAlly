import { test, expect } from "@playwright/test";
import {
  DEFAULT_TICKERS,
  FRESH_DB,
  ensureInWatchlist,
  ensureNotInWatchlist,
  flattenPosition,
  getPortfolio,
  getPosition,
  getWatchlist,
  waitForPrice,
} from "./helpers";

// API-level contract tests (planning/TEAM_CONTRACTS.md "REST API").

function expectPortfolioShape(p: any) {
  expect(typeof p.cash_balance).toBe("number");
  expect(typeof p.total_value).toBe("number");
  expect(typeof p.positions_value).toBe("number");
  expect(typeof p.unrealized_pnl).toBe("number");
  expect(Array.isArray(p.positions)).toBe(true);
  for (const pos of p.positions) {
    for (const k of ["ticker", "quantity", "avg_cost", "current_price", "market_value", "unrealized_pnl", "pnl_percent"]) {
      expect(pos, `position field ${k}`).toHaveProperty(k);
    }
  }
  expect(p.total_value).toBeCloseTo(p.cash_balance + p.positions_value, 1);
}

test.describe("API: system", () => {
  test("GET /api/health", async ({ request }) => {
    const res = await request.get("/api/health");
    expect(res.status()).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });

  test("static frontend is served at /", async ({ request }) => {
    const res = await request.get("/");
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("text/html");
  });
});

test.describe("API: SSE stream", () => {
  test("GET /api/stream/prices emits price events", async ({ baseURL }) => {
    const controller = new AbortController();
    const res = await fetch(`${baseURL}/api/stream/prices`, { signal: controller.signal });
    try {
      expect(res.status).toBe(200);
      expect(res.headers.get("content-type")).toContain("text/event-stream");
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let payload: any = null;
      const deadline = Date.now() + 10_000;
      while (!payload && Date.now() < deadline) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const m = buf.match(/^data: (.+)$/m);
        if (m) payload = JSON.parse(m[1]);
      }
      expect(payload, "received a data event").not.toBeNull();
      const aapl = payload.AAPL;
      expect(aapl).toBeTruthy();
      for (const k of ["ticker", "price", "previous_price", "timestamp", "change", "change_percent", "direction"]) {
        expect(aapl, `event field ${k}`).toHaveProperty(k);
      }
      expect(["up", "down", "flat"]).toContain(aapl.direction);
    } finally {
      controller.abort();
    }
  });
});

test.describe("API: watchlist", () => {
  test("GET /api/watchlist returns tickers with price fields", async ({ request }) => {
    await waitForPrice(request, "AAPL");
    const res = await request.get("/api/watchlist");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.tickers)).toBe(true);
    const tickers = body.tickers.map((t: any) => t.ticker);
    if (FRESH_DB) expect(tickers).toEqual(DEFAULT_TICKERS);
    for (const t of body.tickers) {
      for (const k of ["ticker", "price", "previous_price", "change", "change_percent", "direction"]) {
        expect(t, `watchlist field ${k}`).toHaveProperty(k);
      }
    }
    const aapl = body.tickers.find((t: any) => t.ticker === "AAPL");
    expect(typeof aapl.price).toBe("number");
  });

  test("POST/DELETE /api/watchlist lifecycle and errors", async ({ request }) => {
    const T = "SHOP";
    await ensureNotInWatchlist(request, T);

    let res = await request.post("/api/watchlist", { data: { ticker: T.toLowerCase() } });
    expect(res.status()).toBe(201);
    expect(await res.json()).toEqual({ ticker: T });
    expect(await getWatchlist(request)).toContain(T);

    res = await request.post("/api/watchlist", { data: { ticker: T } });
    expect(res.status()).toBe(409);
    expect(await res.json()).toHaveProperty("detail");

    res = await request.delete(`/api/watchlist/${T}`);
    expect(res.status()).toBe(200);
    expect(await res.json()).toEqual({ ticker: T });
    expect(await getWatchlist(request)).not.toContain(T);

    res = await request.delete(`/api/watchlist/${T}`);
    expect(res.status()).toBe(404);
    expect(await res.json()).toHaveProperty("detail");
  });

  test("POST /api/watchlist rejects invalid tickers", async ({ request }) => {
    for (const bad of ["123", "TOO_LONG_TICKER", "", "A B"]) {
      const res = await request.post("/api/watchlist", { data: { ticker: bad } });
      expect([400, 422], `ticker ${JSON.stringify(bad)}`).toContain(res.status());
    }
  });
});

test.describe("API: portfolio", () => {
  const T = "NFLX";

  test.beforeEach(async ({ request }) => {
    await ensureInWatchlist(request, T);
    await waitForPrice(request, T);
    await flattenPosition(request, T);
  });

  test("GET /api/portfolio shape", async ({ request }) => {
    const p = await getPortfolio(request);
    expectPortfolioShape(p);
  });

  test("buy then sell round trip", async ({ request }) => {
    const before = await getPortfolio(request);

    let res = await request.post("/api/portfolio/trade", { data: { ticker: T.toLowerCase(), side: "buy", quantity: 1.5 } });
    expect(res.status(), await res.text()).toBe(200);
    let body = await res.json();
    for (const k of ["id", "ticker", "side", "quantity", "price", "executed_at"]) {
      expect(body.trade, `trade field ${k}`).toHaveProperty(k);
    }
    expect(body.trade.ticker).toBe(T);
    expect(body.trade.side).toBe("buy");
    expect(body.trade.quantity).toBe(1.5);
    expectPortfolioShape(body.portfolio);
    // Cash may be rounded to cents server-side, so allow a cent or two of difference.
    expect(Math.abs(body.portfolio.cash_balance - (before.cash_balance - 1.5 * body.trade.price))).toBeLessThan(0.02);
    const pos = body.portfolio.positions.find((x: any) => x.ticker === T);
    expect(pos.quantity).toBe(1.5);
    expect(pos.avg_cost).toBeCloseTo(body.trade.price, 4);

    res = await request.post("/api/portfolio/trade", { data: { ticker: T, side: "sell", quantity: 1.5 } });
    expect(res.status(), await res.text()).toBe(200);
    body = await res.json();
    expect(body.trade.side).toBe("sell");
    expect(body.portfolio.positions.find((x: any) => x.ticker === T)).toBeUndefined();
  });

  test("trade validation errors", async ({ request }) => {
    const before = await getPortfolio(request);

    const cases = [
      { data: { ticker: T, side: "sell", quantity: 1 }, why: "selling shares not owned" },
      { data: { ticker: T, side: "buy", quantity: 100_000_000 }, why: "insufficient cash" },
      { data: { ticker: T, side: "buy", quantity: 0 }, why: "zero quantity" },
      { data: { ticker: T, side: "buy", quantity: -1 }, why: "negative quantity" },
      { data: { ticker: T, side: "hold", quantity: 1 }, why: "invalid side" },
    ];
    for (const c of cases) {
      const res = await request.post("/api/portfolio/trade", { data: c.data });
      expect([400, 422], c.why).toContain(res.status());
      expect(await res.json(), c.why).toHaveProperty("detail");
    }

    const after = await getPortfolio(request);
    expect(after.cash_balance).toBeCloseTo(before.cash_balance, 2);
    expect(await getPosition(request, T)).toBeUndefined();
  });

  test("GET /api/portfolio/history returns snapshots (one recorded after each trade)", async ({ request }) => {
    const count = async () => {
      const res = await request.get("/api/portfolio/history");
      expect(res.status()).toBe(200);
      const body = await res.json();
      for (const s of body.snapshots) {
        expect(typeof s.total_value).toBe("number");
        expect(typeof s.recorded_at).toBe("string");
      }
      return body.snapshots.length as number;
    };
    const before = await count();
    const res = await request.post("/api/portfolio/trade", { data: { ticker: T, side: "buy", quantity: 1 } });
    expect(res.status()).toBe(200);
    expect(await count()).toBeGreaterThan(before);
    await flattenPosition(request, T);
  });
});

test.describe("API: chat (LLM_MOCK=true)", () => {
  test("default mock response", async ({ request }) => {
    const res = await request.post("/api/chat", { data: { message: "hello there" } });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.message).toContain("Mock response");
    expect(body.trades).toEqual([]);
    expect(body.watchlist_changes).toEqual([]);
  });

  test("buy / sell via chat executes trades", async ({ request }) => {
    await waitForPrice(request, "AAPL");
    await flattenPosition(request, "AAPL");

    let res = await request.post("/api/chat", { data: { message: "Please buy 2 AAPL" } });
    expect(res.status()).toBe(200);
    let body = await res.json();
    expect(typeof body.message).toBe("string");
    expect(body.trades).toHaveLength(1);
    expect(body.trades[0]).toMatchObject({ ticker: "AAPL", side: "buy", quantity: 2, status: "executed" });
    expect(typeof body.trades[0].price).toBe("number");
    expect((await getPosition(request, "AAPL"))?.quantity).toBe(2);

    res = await request.post("/api/chat", { data: { message: "sell 2 aapl" } });
    body = await res.json();
    expect(body.trades[0]).toMatchObject({ ticker: "AAPL", side: "sell", quantity: 2, status: "executed" });
    expect(await getPosition(request, "AAPL")).toBeUndefined();
  });

  test("failed trade via chat is reported, not a 500", async ({ request }) => {
    await flattenPosition(request, "AAPL");
    const res = await request.post("/api/chat", { data: { message: "sell 5 AAPL" } });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.trades[0].status).toBe("failed");
    expect(body.trades[0].error).toBeTruthy();
  });

  test("watch via chat adds to watchlist", async ({ request }) => {
    const T = "UBER";
    await ensureNotInWatchlist(request, T);
    const res = await request.post("/api/chat", { data: { message: `watch ${T}` } });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.watchlist_changes[0]).toMatchObject({ ticker: T, action: "add", status: "executed" });
    expect(await getWatchlist(request)).toContain(T);
    await ensureNotInWatchlist(request, T);
  });

  test("GET /api/chat/history returns stored messages with actions", async ({ request }) => {
    const marker = `api history ${Date.now()}`;
    await request.post("/api/chat", { data: { message: marker } });
    const res = await request.get("/api/chat/history");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.messages)).toBe(true);
    for (const m of body.messages) {
      for (const k of ["id", "role", "content", "actions", "created_at"]) expect(m, `message field ${k}`).toHaveProperty(k);
      expect(["user", "assistant"]).toContain(m.role);
    }
    const idx = body.messages.findIndex((m: any) => m.role === "user" && m.content === marker);
    expect(idx).toBeGreaterThanOrEqual(0);
    expect(body.messages[idx + 1]?.role).toBe("assistant");
  });
});
