"use client";

import { useEffect, useRef, useState } from "react";
import type { ConnectionStatus, PriceMap, PricePoint, PriceUpdate } from "./types";

export const MAX_HISTORY_POINTS = 1200;

export type PriceHistory = Record<string, PricePoint[]>;

/**
 * Fold one SSE payload into the accumulated per-ticker history.
 * Points are keyed by whole seconds; a second tick in the same second replaces the last point.
 * Returns the same object if nothing changed.
 */
export function appendHistory(
  history: PriceHistory,
  updates: Record<string, PriceUpdate>,
  maxPoints = MAX_HISTORY_POINTS,
): PriceHistory {
  let next: PriceHistory | null = null;
  for (const [ticker, u] of Object.entries(updates)) {
    if (!u || typeof u.price !== "number" || !Number.isFinite(u.price)) continue;
    const time = Math.floor(u.timestamp || Date.now() / 1000);
    const prev = history[ticker] ?? [];
    const last = prev[prev.length - 1];
    let series: PricePoint[];
    if (last && last.time === time) {
      if (last.value === u.price) continue;
      series = [...prev.slice(0, -1), { time, value: u.price }];
    } else if (last && time < last.time) {
      continue; // out-of-order event
    } else {
      series = [...prev, { time, value: u.price }];
      if (series.length > maxPoints) series = series.slice(series.length - maxPoints);
    }
    next = next ?? { ...history };
    next[ticker] = series;
  }
  return next ?? history;
}

export interface PriceStreamState {
  prices: PriceMap;
  history: PriceHistory;
  status: ConnectionStatus;
  /** First price seen for each ticker since page load (session open). */
  opens: Record<string, number>;
}

/** Record the first price seen per ticker; returns the same object if nothing is new. */
export function recordOpens(
  opens: Record<string, number>,
  updates: Record<string, PriceUpdate>,
): Record<string, number> {
  let next: Record<string, number> | null = null;
  for (const [ticker, u] of Object.entries(updates)) {
    if (opens[ticker] !== undefined || !u || !Number.isFinite(u.price)) continue;
    next = next ?? { ...opens };
    next[ticker] = u.price;
  }
  return next ?? opens;
}

/**
 * Subscribe to the SSE price stream. Tracks connection status and manually
 * reconnects if the browser gives up (readyState CLOSED).
 */
export function usePriceStream(url: string): PriceStreamState {
  const [prices, setPrices] = useState<PriceMap>({});
  const [history, setHistory] = useState<PriceHistory>({});
  const [opens, setOpens] = useState<Record<string, number>>({});
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      return;
    }
    let es: EventSource | null = null;
    let disposed = false;
    let attempts = 0;

    const connect = () => {
      if (disposed) return;
      es = new EventSource(url);
      es.onopen = () => {
        attempts = 0;
        setStatus("connected");
      };
      es.onmessage = (ev: MessageEvent<string>) => {
        let data: Record<string, PriceUpdate>;
        try {
          data = JSON.parse(ev.data);
        } catch {
          return;
        }
        if (!data || typeof data !== "object") return;
        setStatus("connected");
        setPrices((prev) => ({ ...prev, ...data }));
        setHistory((prev) => appendHistory(prev, data));
        setOpens((prev) => recordOpens(prev, data));
      };
      es.onerror = () => {
        if (!es) return;
        if (es.readyState === EventSource.CLOSED) {
          es.close();
          setStatus("disconnected");
          attempts += 1;
          const delay = Math.min(10000, 1000 * 2 ** Math.min(attempts - 1, 4));
          retryRef.current = setTimeout(connect, delay);
        } else {
          setStatus("reconnecting");
        }
      };
    };

    connect();
    return () => {
      disposed = true;
      if (retryRef.current) clearTimeout(retryRef.current);
      es?.close();
    };
  }, [url]);

  return { prices, history, status, opens };
}
