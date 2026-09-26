"use client";

import { useState, type FormEvent } from "react";
import type { Side, Trade } from "@/lib/types";
import { formatPrice, formatQty, formatUsd } from "@/lib/format";

interface Props {
  ticker: string;
  onTickerChange: (ticker: string) => void;
  price: number | null;
  cash: number | null;
  onTrade: (ticker: string, quantity: number, side: Side) => Promise<Trade>;
}

export default function TradeBar({ ticker, onTickerChange, price, cash, onTrade }: Props) {
  const [qty, setQty] = useState("");
  const [busy, setBusy] = useState<Side | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const quantity = Number(qty);
  const estimate = price != null && quantity > 0 ? price * quantity : null;

  const submit = async (side: Side) => {
    const t = ticker.trim().toUpperCase();
    setNotice(null);
    if (!t) {
      setError("Enter a ticker symbol.");
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError("Enter a quantity greater than 0.");
      return;
    }
    setBusy(side);
    setError(null);
    try {
      const trade = await onTrade(t, quantity, side);
      setNotice(
        `${trade.side === "buy" ? "Bought" : "Sold"} ${formatQty(trade.quantity)} ${trade.ticker} at ${formatPrice(trade.price)}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trade failed");
    } finally {
      setBusy(null);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void submit("buy");
  };

  return (
    <form onSubmit={onSubmit} aria-label="Trade" className="flex flex-wrap items-center gap-2 px-3 py-2.5">
      <label className="flex items-center gap-1.5 text-xs text-muted">
        Symbol
        <input
          data-testid="trade-ticker-input"
          value={ticker}
          onChange={(e) => onTickerChange(e.target.value.toUpperCase())}
          maxLength={10}
          autoComplete="off"
          spellCheck={false}
          className="num w-24 rounded border border-line bg-ink px-2 py-1.5 text-sm uppercase text-text focus:border-blue focus:outline-none"
        />
      </label>
      <label className="flex items-center gap-1.5 text-xs text-muted">
        Qty
        <input
          data-testid="trade-quantity-input"
          type="number"
          inputMode="decimal"
          min="0"
          step="any"
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          placeholder="0"
          className="num w-24 rounded border border-line bg-ink px-2 py-1.5 text-sm text-text placeholder:text-dim focus:border-blue focus:outline-none"
        />
      </label>
      <button
        type="button"
        data-testid="trade-buy-button"
        disabled={busy !== null}
        onClick={() => void submit("buy")}
        className="rounded bg-purple px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-purple-hi disabled:opacity-50"
      >
        {busy === "buy" ? "Buying…" : "Buy"}
      </button>
      <button
        type="button"
        data-testid="trade-sell-button"
        disabled={busy !== null}
        onClick={() => void submit("sell")}
        className="rounded border border-purple px-4 py-1.5 text-sm font-semibold text-text transition-colors hover:bg-purple/25 disabled:opacity-50"
      >
        {busy === "sell" ? "Selling…" : "Sell"}
      </button>
      <span className="num ml-auto text-xs text-muted">
        {estimate != null ? `≈ ${formatUsd(estimate)}` : ""}
        {cash != null && <span className="ml-3">Buying power {formatUsd(cash)}</span>}
      </span>
      <div className="basis-full text-xs" aria-live="polite">
        {error && (
          <p data-testid="trade-error" role="alert" className="text-down">
            {error}
          </p>
        )}
        {notice && !error && (
          <p data-testid="trade-notice" className="text-up">
            {notice}
          </p>
        )}
      </div>
    </form>
  );
}
