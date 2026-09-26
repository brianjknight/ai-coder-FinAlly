"use client";

import { useState, type FormEvent } from "react";
import type { PricePoint, PriceUpdate } from "@/lib/types";
import { formatPercent, formatPrice, signClass } from "@/lib/format";
import Sparkline from "./Sparkline";
import { useFlash } from "./useFlash";

export interface WatchlistRowData {
  ticker: string;
  price: number | null;
  /** Percent change since the session open (first price seen on this page). */
  changePercent: number | null;
  points: PricePoint[];
}

interface RowProps {
  row: WatchlistRowData;
  selected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

function WatchlistRow({ row, selected, onSelect, onRemove }: RowProps) {
  const flashRef = useFlash<HTMLTableCellElement>(row.price);
  const { ticker } = row;
  return (
    <tr
      data-testid={`watchlist-row-${ticker}`}
      aria-selected={selected}
      onClick={() => onSelect(ticker)}
      className={`group cursor-pointer border-b border-line/60 transition-colors hover:bg-raised ${
        selected ? "bg-raised shadow-[inset_2px_0_0_var(--color-accent)]" : ""
      }`}
    >
      <td className="py-1.5 pl-3 pr-2">
        <button
          type="button"
          className="font-semibold tracking-wide text-text focus-visible:text-accent"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(ticker);
          }}
        >
          {ticker}
        </button>
      </td>
      <td
        ref={flashRef}
        data-testid={`watchlist-price-${ticker}`}
        className="flash-cell num rounded-sm px-1.5 py-1.5 text-right text-text"
      >
        {formatPrice(row.price)}
      </td>
      <td className={`num px-1.5 py-1.5 text-right text-xs ${signClass(row.changePercent)}`}>
        {formatPercent(row.changePercent)}
      </td>
      <td className="py-1 pl-1.5 pr-1">
        <Sparkline points={row.points} />
      </td>
      <td className="w-6 pr-2 text-right">
        <button
          type="button"
          data-testid={`watchlist-remove-${ticker}`}
          aria-label={`Remove ${ticker} from watchlist`}
          title={`Remove ${ticker}`}
          onClick={(e) => {
            e.stopPropagation();
            onRemove(ticker);
          }}
          className="rounded px-1 text-dim opacity-40 transition-opacity hover:text-down group-hover:opacity-100 focus-visible:opacity-100"
        >
          ×
        </button>
      </td>
    </tr>
  );
}

interface Props {
  rows: WatchlistRowData[];
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<void>;
  onRemove: (ticker: string) => Promise<void>;
}

export function buildWatchlistRows(
  tickers: string[],
  prices: Record<string, PriceUpdate>,
  history: Record<string, PricePoint[]>,
  opens: Record<string, number>,
  fallback: Record<string, number | null> = {},
): WatchlistRowData[] {
  return tickers.map((ticker) => {
    const price = prices[ticker]?.price ?? fallback[ticker] ?? null;
    const open = opens[ticker];
    const changePercent = price != null && open ? ((price - open) / open) * 100 : null;
    return { ticker, price, changePercent, points: history[ticker] ?? [] };
  });
}

export default function Watchlist({ rows, selected, onSelect, onAdd, onRemove }: Props) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    if (!/^[A-Z.]{1,10}$/.test(ticker)) {
      setError("Use 1–10 letters, e.g. PYPL");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onAdd(ticker);
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add ticker");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (ticker: string) => {
    setError(null);
    try {
      await onRemove(ticker);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove ticker");
    }
  };

  return (
    <section data-testid="watchlist" aria-label="Watchlist" className="flex min-h-0 flex-col">
      <div className="flex items-baseline justify-between px-3 pb-1.5 pt-2.5">
        <h2 className="text-[13px] font-semibold text-text">Watchlist</h2>
        <span className="text-xs text-dim">{rows.length} symbols</span>
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 ? (
          <p className="px-3 py-6 text-sm text-muted">No symbols yet. Add one below to start streaming.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="text-left text-[11px] text-dim">
                <th className="pb-1 pl-3 font-normal">Symbol</th>
                <th className="px-1.5 pb-1 text-right font-normal">Last</th>
                <th className="px-1.5 pb-1 text-right font-normal" title="Change since this page started streaming">
                  Session
                </th>
                <th className="pb-1 pl-1.5 font-normal">Trend</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <WatchlistRow
                  key={row.ticker}
                  row={row}
                  selected={row.ticker === selected}
                  onSelect={onSelect}
                  onRemove={remove}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
      <form onSubmit={submit} className="border-t border-line px-3 py-2.5">
        <div className="flex gap-1.5">
          <input
            data-testid="watchlist-add-input"
            aria-label="Ticker to add"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            placeholder="Add symbol"
            maxLength={10}
            autoComplete="off"
            spellCheck={false}
            className="num min-w-0 flex-1 rounded border border-line bg-ink px-2 py-1 text-sm uppercase text-text placeholder:normal-case placeholder:text-dim focus:border-blue focus:outline-none"
          />
          <button
            type="submit"
            data-testid="watchlist-add-button"
            disabled={busy || !input.trim()}
            className="rounded border border-blue/60 px-3 py-1 text-sm font-medium text-blue transition-colors hover:bg-blue/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Add
          </button>
        </div>
        {error && (
          <p role="alert" data-testid="watchlist-error" className="mt-1.5 text-xs text-down">
            {error}
          </p>
        )}
      </form>
    </section>
  );
}
