import { describe, expect, it } from "vitest";
import { appendHistory, recordOpens } from "@/lib/usePriceStream";
import { livePositions, portfolioTotals } from "@/lib/portfolio";
import { pnlColor, squarify } from "@/lib/treemap";
import { formatPercent, formatSignedUsd, formatUsd, signClass } from "@/lib/format";
import { extractDetail } from "@/lib/api";
import { snapshotsToSeries } from "@/components/PnlChart";
import type { Portfolio, PriceUpdate } from "@/lib/types";

const tick = (ticker: string, price: number, timestamp: number): PriceUpdate => ({
  ticker,
  price,
  previous_price: price,
  timestamp,
  change: 0,
  change_percent: 0,
  direction: "flat",
});

describe("appendHistory", () => {
  it("appends new points per ticker", () => {
    let h = appendHistory({}, { AAPL: tick("AAPL", 190, 100) });
    h = appendHistory(h, { AAPL: tick("AAPL", 191, 101), MSFT: tick("MSFT", 400, 101) });
    expect(h.AAPL).toEqual([
      { time: 100, value: 190 },
      { time: 101, value: 191 },
    ]);
    expect(h.MSFT).toHaveLength(1);
  });

  it("replaces the last point when a tick lands in the same second", () => {
    let h = appendHistory({}, { AAPL: tick("AAPL", 190, 100.1) });
    h = appendHistory(h, { AAPL: tick("AAPL", 190.5, 100.6) });
    expect(h.AAPL).toEqual([{ time: 100, value: 190.5 }]);
  });

  it("returns the same object when nothing changes and caps length", () => {
    const h = appendHistory({}, { AAPL: tick("AAPL", 190, 100) });
    expect(appendHistory(h, { AAPL: tick("AAPL", 190, 100) })).toBe(h);
    let capped = {};
    for (let i = 0; i < 20; i++) capped = appendHistory(capped, { X: tick("X", i, i + 1) }, 5);
    expect((capped as Record<string, unknown[]>).X).toHaveLength(5);
  });

  it("records the first price seen per ticker only once", () => {
    let o = recordOpens({}, { AAPL: tick("AAPL", 190, 1) });
    o = recordOpens(o, { AAPL: tick("AAPL", 200, 2), TSLA: tick("TSLA", 250, 2) });
    expect(o).toEqual({ AAPL: 190, TSLA: 250 });
  });
});

describe("portfolio calculations", () => {
  const portfolio: Portfolio = {
    cash_balance: 5000,
    total_value: 0,
    positions_value: 0,
    unrealized_pnl: 0,
    positions: [
      { ticker: "AAPL", quantity: 10, avg_cost: 100, current_price: 100, market_value: 1000, unrealized_pnl: 0, pnl_percent: 0 },
      { ticker: "TSLA", quantity: 2, avg_cost: 250, current_price: 240, market_value: 480, unrealized_pnl: -20, pnl_percent: -4 },
    ],
  };

  it("reprices positions using live prices, falling back to server price", () => {
    const pos = livePositions(portfolio, { AAPL: tick("AAPL", 110, 1) });
    expect(pos[0].current_price).toBe(110);
    expect(pos[0].market_value).toBe(1100);
    expect(pos[0].unrealized_pnl).toBe(100);
    expect(pos[0].pnl_percent).toBeCloseTo(10);
    expect(pos[1].current_price).toBe(240);
    expect(pos[1].unrealized_pnl).toBe(-20);
  });

  it("computes totals", () => {
    const pos = livePositions(portfolio, { AAPL: tick("AAPL", 110, 1) });
    expect(portfolioTotals(portfolio, pos)).toEqual({
      cash: 5000,
      positionsValue: 1580,
      totalValue: 6580,
      unrealizedPnl: 80,
    });
    expect(portfolioTotals(null, [])).toEqual({ cash: 0, positionsValue: 0, totalValue: 0, unrealizedPnl: 0 });
  });
});

describe("treemap", () => {
  it("fills the rectangle with areas proportional to value", () => {
    const rects = squarify(
      [
        { value: 6, data: "a" },
        { value: 3, data: "b" },
        { value: 1, data: "c" },
      ],
      100,
      50,
    );
    expect(rects).toHaveLength(3);
    const area = rects.reduce((s, r) => s + r.w * r.h, 0);
    expect(area).toBeCloseTo(5000);
    const a = rects.find((r) => r.data === "a")!;
    expect(a.w * a.h).toBeCloseTo(3000);
    for (const r of rects) {
      expect(r.x).toBeGreaterThanOrEqual(-1e-9);
      expect(r.y).toBeGreaterThanOrEqual(-1e-9);
      expect(r.x + r.w).toBeLessThanOrEqual(100 + 1e-9);
      expect(r.y + r.h).toBeLessThanOrEqual(50 + 1e-9);
    }
  });

  it("ignores zero values and empty input", () => {
    expect(squarify([], 10, 10)).toEqual([]);
    expect(squarify([{ value: 0, data: 1 }], 10, 10)).toEqual([]);
  });

  it("colors profit green and loss red", () => {
    expect(pnlColor(3)).toContain("47, 191, 113");
    expect(pnlColor(-3)).toContain("239, 90, 90");
    expect(pnlColor(0)).toContain("125, 136, 152");
  });
});

describe("formatting", () => {
  it("formats currency and percentages", () => {
    expect(formatUsd(10000)).toBe("$10,000.00");
    expect(formatUsd(null)).toBe("—");
    expect(formatSignedUsd(-12.5)).toBe("-$12.50");
    expect(formatSignedUsd(3)).toBe("+$3.00");
    expect(formatPercent(1.234)).toBe("+1.23%");
    expect(formatPercent(-0.5)).toBe("-0.50%");
    expect(formatPercent(0.0001)).toBe("0.00%");
    expect(signClass(1)).toBe("text-up");
    expect(signClass(-1)).toBe("text-down");
    expect(signClass(0)).toBe("text-muted");
  });

  it("extracts API error details", () => {
    expect(extractDetail({ detail: "Insufficient cash" })).toBe("Insufficient cash");
    expect(extractDetail({ detail: [{ msg: "field required" }] })).toBe("field required");
    expect(extractDetail(null)).toBeNull();
  });

  it("converts snapshots to ascending unique-second series", () => {
    const s = snapshotsToSeries([
      { total_value: 10100, recorded_at: "2026-01-01T00:00:10Z" },
      { total_value: 10000, recorded_at: "2026-01-01T00:00:00Z" },
      { total_value: 10150, recorded_at: "2026-01-01T00:00:10.500Z" },
    ]);
    expect(s.map((p) => p.value)).toEqual([10000, 10150]);
    expect(s[1].time - s[0].time).toBe(10);
  });
});
