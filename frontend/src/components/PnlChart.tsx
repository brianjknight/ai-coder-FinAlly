"use client";

import { useEffect, useRef } from "react";
import {
  BaselineSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Snapshot } from "@/lib/types";
import { baseChartOptions, CHART_COLORS } from "@/lib/chartTheme";
import { toLocalChartTime } from "@/lib/format";

export const STARTING_VALUE = 10000;

/** Convert snapshots into strictly ascending, one-per-second chart points. */
export function snapshotsToSeries(snapshots: Snapshot[]): { time: number; value: number }[] {
  const out: { time: number; value: number }[] = [];
  const sorted = [...snapshots]
    .map((s) => ({ t: Date.parse(s.recorded_at), v: s.total_value }))
    .filter((s) => Number.isFinite(s.t) && Number.isFinite(s.v))
    .sort((a, b) => a.t - b.t);
  for (const s of sorted) {
    const time = Math.floor(s.t / 1000);
    const last = out[out.length - 1];
    if (last && last.time === time) last.value = s.v;
    else out.push({ time, value: s.v });
  }
  return out;
}

interface Props {
  snapshots: Snapshot[];
  liveValue: number | null;
}

export default function PnlChart({ snapshots, liveValue }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Baseline"> | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const opts = baseChartOptions();
    const chart = createChart(el, {
      ...opts,
      timeScale: { ...opts.timeScale, secondsVisible: false },
    });
    const series = chart.addSeries(BaselineSeries, {
      baseValue: { type: "price", price: STARTING_VALUE },
      topLineColor: CHART_COLORS.up,
      topFillColor1: "rgba(47, 191, 113, 0.28)",
      topFillColor2: "rgba(47, 191, 113, 0.03)",
      bottomLineColor: CHART_COLORS.down,
      bottomFillColor1: "rgba(239, 90, 90, 0.03)",
      bottomFillColor2: "rgba(239, 90, 90, 0.28)",
      lineWidth: 2,
      priceLineVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    const points = snapshotsToSeries(snapshots);
    if (liveValue != null && Number.isFinite(liveValue)) {
      const now = Math.floor(Date.now() / 1000);
      const last = points[points.length - 1];
      if (!last || now > last.time) points.push({ time: now, value: liveValue });
    }
    series.setData(points.map((p) => ({ time: toLocalChartTime(p.time) as UTCTimestamp, value: p.value })));
    chartRef.current?.timeScale().fitContent();
  }, [snapshots, liveValue]);

  return (
    <section aria-label="Portfolio value over time" className="flex h-full min-h-0 flex-col">
      <div className="flex items-baseline justify-between px-3 pb-1 pt-2.5">
        <h2 className="text-[13px] font-semibold text-text">Portfolio value</h2>
        <span className="text-xs text-dim">vs. $10,000 start</span>
      </div>
      <div data-testid="pnl-chart" ref={containerRef} className="relative min-h-[140px] flex-1" />
    </section>
  );
}
