"use client";

import { useEffect, useRef } from "react";
import {
  AreaSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { PricePoint } from "@/lib/types";
import { baseChartOptions, CHART_COLORS } from "@/lib/chartTheme";
import { formatPercent, formatPrice, signClass, toLocalChartTime } from "@/lib/format";

interface Props {
  ticker: string | null;
  points: PricePoint[];
  price: number | null;
  open: number | null;
}

export default function PriceChart({ ticker, points, price, open }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = createChart(el, baseChartOptions());
    const series = chart.addSeries(AreaSeries, {
      lineColor: CHART_COLORS.blue,
      lineWidth: 2,
      topColor: "rgba(32, 157, 215, 0.28)",
      bottomColor: "rgba(32, 157, 215, 0.02)",
      priceLineColor: CHART_COLORS.accent,
      priceLineWidth: 1,
      lastValueVisible: true,
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
    const chart = chartRef.current;
    if (!series || !chart) return;
    const data = points.map((p) => ({ time: toLocalChartTime(p.time) as UTCTimestamp, value: p.value }));
    series.setData(data);
    // Keep the whole session in view as ticks accumulate (and after switching tickers).
    chart.timeScale().fitContent();
  }, [points, ticker]);

  const change = price != null && open ? ((price - open) / open) * 100 : null;

  return (
    <section aria-label="Price chart" className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 px-3 pb-1 pt-2.5">
        <h2 className="text-[22px] font-semibold leading-none tracking-wide text-text" data-testid="selected-ticker">
          {ticker ?? "—"}
        </h2>
        <span className="num text-[22px] leading-none text-text">{formatPrice(price)}</span>
        <span className={`num text-sm ${signClass(change)}`}>{formatPercent(change)} this session</span>
        {points.length < 2 && ticker && <span className="text-xs text-dim">Collecting ticks…</span>}
      </div>
      <div data-testid="main-chart" ref={containerRef} className="relative min-h-[180px] flex-1" />
    </section>
  );
}
