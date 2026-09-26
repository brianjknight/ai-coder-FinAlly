"use client";

import type { ConnectionStatus } from "@/lib/types";
import { formatPercent, formatSignedUsd, formatUsd, signClass } from "@/lib/format";
import { useFlash } from "./useFlash";

const STATUS_STYLE: Record<ConnectionStatus, { dot: string; label: string }> = {
  connected: { dot: "bg-up shadow-[0_0_6px_var(--color-up)]", label: "Live" },
  reconnecting: { dot: "bg-accent", label: "Reconnecting" },
  disconnected: { dot: "bg-down", label: "Disconnected" },
};

interface Props {
  totalValue: number | null;
  cash: number | null;
  unrealizedPnl: number | null;
  startingValue: number;
  status: ConnectionStatus;
}

export default function Header({ totalValue, cash, unrealizedPnl, startingValue, status }: Props) {
  const valueRef = useFlash<HTMLSpanElement>(totalValue == null ? null : Math.round(totalValue * 100) / 100);
  const s = STATUS_STYLE[status];
  const allTime = totalValue != null ? totalValue - startingValue : null;
  const allTimePct = allTime != null ? (allTime / startingValue) * 100 : null;

  return (
    <header className="flex flex-wrap items-center gap-x-8 gap-y-2 border-b border-line bg-panel px-4 py-2.5">
      <div className="flex items-baseline gap-2">
        <span className="text-lg font-semibold tracking-tight text-text">
          Fin<span className="text-accent">Ally</span>
        </span>
        <span className="hidden text-xs text-dim sm:inline">AI trading workstation</span>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-xs text-muted">Portfolio</span>
        <span
          ref={valueRef}
          data-testid="header-total-value"
          className="flash-cell num rounded px-1 text-[22px] font-medium leading-none text-accent"
        >
          {formatUsd(totalValue)}
        </span>
        <span className={`num text-xs ${signClass(allTime)}`}>
          {formatSignedUsd(allTime)} ({formatPercent(allTimePct)})
        </span>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-xs text-muted">Cash</span>
        <span data-testid="header-cash" className="num text-[15px] text-text">
          {formatUsd(cash)}
        </span>
      </div>

      <div className="hidden items-baseline gap-2 md:flex">
        <span className="text-xs text-muted">Unrealized</span>
        <span className={`num text-[15px] ${signClass(unrealizedPnl)}`}>{formatSignedUsd(unrealizedPnl)}</span>
      </div>

      <div
        className="ml-auto flex items-center gap-2 text-xs text-muted"
        data-testid="connection-status"
        data-status={status}
        role="status"
        aria-label={`Price stream ${s.label.toLowerCase()}`}
        title={`Price stream: ${s.label}`}
      >
        <span className={`inline-block h-2 w-2 rounded-full ${s.dot}`} />
        {s.label}
      </div>
    </header>
  );
}
