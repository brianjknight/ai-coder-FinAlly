"use client";

import { useEffect, useRef, useState } from "react";
import type { Position } from "@/lib/types";
import { pnlColor, squarify } from "@/lib/treemap";
import { formatPercent, formatUsd } from "@/lib/format";

interface Props {
  positions: Position[];
  onSelect?: (ticker: string) => void;
}

export default function Heatmap({ positions, onSelect }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 400, h: 220 });

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (r && r.width > 0 && r.height > 0) setSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const total = positions.reduce((s, p) => s + Math.max(0, p.market_value), 0);
  const rects = squarify(
    positions.map((p) => ({ value: Math.max(0, p.market_value), data: p })),
    size.w,
    size.h,
  );

  return (
    <section aria-label="Portfolio heatmap" className="flex h-full min-h-0 flex-col">
      <div className="flex items-baseline justify-between px-3 pb-1.5 pt-2.5">
        <h2 className="text-[13px] font-semibold text-text">Allocation</h2>
        <span className="text-xs text-dim">size = weight, color = P&amp;L</span>
      </div>
      <div data-testid="heatmap" ref={ref} className="relative mx-3 mb-3 min-h-[140px] flex-1">
        {rects.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center rounded border border-dashed border-line text-sm text-muted">
            No positions yet. Buy something to see it here.
          </div>
        ) : (
          rects.map((r) => {
            const p = r.data;
            const weight = total > 0 ? (p.market_value / total) * 100 : 0;
            const small = r.w < 64 || r.h < 40;
            return (
              <button
                type="button"
                key={p.ticker}
                data-testid={`heatmap-tile-${p.ticker}`}
                onClick={() => onSelect?.(p.ticker)}
                title={`${p.ticker}: ${formatUsd(p.market_value)} (${weight.toFixed(1)}%), P&L ${formatPercent(p.pnl_percent)}`}
                className="absolute overflow-hidden border border-ink p-1.5 text-left transition-[filter] hover:brightness-125"
                style={{
                  left: `${(r.x / size.w) * 100}%`,
                  top: `${(r.y / size.h) * 100}%`,
                  width: `${(r.w / size.w) * 100}%`,
                  height: `${(r.h / size.h) * 100}%`,
                  backgroundColor: pnlColor(p.pnl_percent),
                }}
              >
                <span className={`block font-semibold leading-tight text-text ${small ? "text-[11px]" : "text-sm"}`}>
                  {p.ticker}
                </span>
                {!small && (
                  <span className="num block text-xs leading-tight text-text/80">{formatPercent(p.pnl_percent)}</span>
                )}
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}
