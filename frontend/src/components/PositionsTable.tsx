import type { Position } from "@/lib/types";
import { formatPercent, formatPrice, formatQty, formatSignedUsd, formatUsd, signClass } from "@/lib/format";

interface Props {
  positions: Position[];
  onSelect?: (ticker: string) => void;
}

export default function PositionsTable({ positions, onSelect }: Props) {
  return (
    <section aria-label="Positions" className="flex h-full min-h-0 flex-col">
      <div className="flex items-baseline justify-between px-3 pb-1.5 pt-2.5">
        <h2 className="text-[13px] font-semibold text-text">Positions</h2>
        <span className="text-xs text-dim">{positions.length} open</span>
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-auto">
        <table data-testid="positions-table" className="w-full border-collapse text-sm">
          <thead className="sticky top-0 bg-panel">
            <tr className="text-[11px] text-dim">
              <th className="px-3 pb-1 text-left font-normal">Symbol</th>
              <th className="px-2 pb-1 text-right font-normal">Qty</th>
              <th className="px-2 pb-1 text-right font-normal">Avg cost</th>
              <th className="px-2 pb-1 text-right font-normal">Last</th>
              <th className="px-2 pb-1 text-right font-normal">Value</th>
              <th className="px-2 pb-1 text-right font-normal">Unrealized</th>
              <th className="px-3 pb-1 text-right font-normal">Return</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-5 text-muted">
                  No open positions. Use the trade bar or ask FinAlly to buy.
                </td>
              </tr>
            ) : (
              positions.map((p) => (
                <tr
                  key={p.ticker}
                  data-testid={`position-row-${p.ticker}`}
                  onClick={() => onSelect?.(p.ticker)}
                  className="cursor-pointer border-t border-line/60 hover:bg-raised"
                >
                  <td className="px-3 py-1.5 font-semibold">{p.ticker}</td>
                  <td className="num px-2 py-1.5 text-right">{formatQty(p.quantity)}</td>
                  <td className="num px-2 py-1.5 text-right text-muted">{formatPrice(p.avg_cost)}</td>
                  <td className="num px-2 py-1.5 text-right">{formatPrice(p.current_price)}</td>
                  <td className="num px-2 py-1.5 text-right">{formatUsd(p.market_value)}</td>
                  <td className={`num px-2 py-1.5 text-right ${signClass(p.unrealized_pnl)}`}>
                    {formatSignedUsd(p.unrealized_pnl)}
                  </td>
                  <td className={`num px-3 py-1.5 text-right ${signClass(p.pnl_percent)}`}>
                    {formatPercent(p.pnl_percent)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
