"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, STREAM_URL } from "@/lib/api";
import { usePriceStream } from "@/lib/usePriceStream";
import { livePositions, portfolioTotals } from "@/lib/portfolio";
import type { Portfolio, Side, Snapshot, WatchlistEntry } from "@/lib/types";
import Header from "./Header";
import Watchlist, { buildWatchlistRows } from "./Watchlist";
import PriceChart from "./PriceChart";
import PnlChart, { STARTING_VALUE } from "./PnlChart";
import Heatmap from "./Heatmap";
import PositionsTable from "./PositionsTable";
import TradeBar from "./TradeBar";
import ChatPanel from "./ChatPanel";

const PORTFOLIO_REFRESH_MS = 15_000;
const HISTORY_REFRESH_MS = 30_000;
const WATCHLIST_REFRESH_MS = 30_000;

export default function Terminal() {
  const { prices, history, status, opens } = usePriceStream(STREAM_URL);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tradeTicker, setTradeTicker] = useState<string | null>(null);
  const [chatCollapsed, setChatCollapsed] = useState(false);

  // Each refresher fetches, then updates state from the promise callback; failures keep the last known data.
  const refreshPortfolio = useCallback(
    () =>
      api
        .getPortfolio()
        .then((p) => setPortfolio(p))
        .catch(() => undefined),
    [],
  );
  const refreshHistory = useCallback(
    () =>
      api
        .getHistory()
        .then((res) => setSnapshots(res.snapshots ?? []))
        .catch(() => undefined),
    [],
  );
  const refreshWatchlist = useCallback(
    () =>
      api
        .getWatchlist()
        .then((res) => setWatchlist(res.tickers ?? []))
        .catch(() => undefined),
    [],
  );

  useEffect(() => {
    void refreshPortfolio();
    void refreshHistory();
    void refreshWatchlist();
    const a = setInterval(refreshPortfolio, PORTFOLIO_REFRESH_MS);
    const b = setInterval(refreshHistory, HISTORY_REFRESH_MS);
    const c = setInterval(refreshWatchlist, WATCHLIST_REFRESH_MS);
    return () => {
      clearInterval(a);
      clearInterval(b);
      clearInterval(c);
    };
  }, [refreshPortfolio, refreshHistory, refreshWatchlist]);

  const tickers = useMemo(() => watchlist.map((w) => w.ticker), [watchlist]);
  const fallbackPrices = useMemo(
    () => Object.fromEntries(watchlist.map((w) => [w.ticker, w.price])),
    [watchlist],
  );
  const rows = useMemo(
    () => buildWatchlistRows(tickers, prices, history, opens, fallbackPrices),
    [tickers, prices, history, opens, fallbackPrices],
  );
  const positions = useMemo(() => livePositions(portfolio, prices), [portfolio, prices]);
  const totals = portfolioTotals(portfolio, positions);

  const selectedTicker = selected ?? tickers[0] ?? null;
  const selectedPrice = selectedTicker
    ? (prices[selectedTicker]?.price ?? fallbackPrices[selectedTicker] ?? null)
    : null;

  const select = useCallback((ticker: string) => {
    setSelected(ticker);
    setTradeTicker(ticker);
  }, []);

  const addTicker = useCallback(
    async (ticker: string) => {
      await api.addTicker(ticker);
      await refreshWatchlist();
    },
    [refreshWatchlist],
  );

  const removeTicker = useCallback(
    async (ticker: string) => {
      await api.removeTicker(ticker);
      setWatchlist((cur) => cur.filter((w) => w.ticker !== ticker));
      setSelected((cur) => (cur === ticker ? null : cur));
      void refreshWatchlist();
    },
    [refreshWatchlist],
  );

  const trade = useCallback(
    async (ticker: string, quantity: number, side: Side) => {
      const res = await api.trade(ticker, quantity, side);
      setPortfolio(res.portfolio);
      void refreshHistory();
      return res.trade;
    },
    [refreshHistory],
  );

  const onChatActions = useCallback(() => {
    void refreshPortfolio();
    void refreshHistory();
    void refreshWatchlist();
  }, [refreshPortfolio, refreshHistory, refreshWatchlist]);

  return (
    <div className="flex min-h-screen flex-col bg-ink lg:h-screen lg:overflow-hidden">
      <Header
        totalValue={portfolio ? totals.totalValue : null}
        cash={portfolio ? totals.cash : null}
        unrealizedPnl={portfolio ? totals.unrealizedPnl : null}
        startingValue={STARTING_VALUE}
        status={status}
      />
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <div className="grid min-h-0 flex-1 gap-px bg-line lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[330px_minmax(0,1fr)]">
          <div className="flex min-h-0 flex-col bg-panel max-lg:h-[420px]">
            <Watchlist
              rows={rows}
              selected={selectedTicker}
              onSelect={select}
              onAdd={addTicker}
              onRemove={removeTicker}
            />
          </div>

          <div className="grid min-h-0 gap-px bg-line lg:grid-rows-[minmax(220px,1.25fr)_auto_minmax(170px,1fr)_minmax(130px,0.8fr)]">
            <div className="min-h-0 bg-panel max-lg:h-[340px]">
              <PriceChart
                ticker={selectedTicker}
                points={selectedTicker ? (history[selectedTicker] ?? []) : []}
                price={selectedPrice}
                open={selectedTicker ? (opens[selectedTicker] ?? null) : null}
              />
            </div>
            <div className="bg-panel">
              <TradeBar
                ticker={tradeTicker ?? selectedTicker ?? ""}
                onTickerChange={setTradeTicker}
                price={(() => {
                  const t = tradeTicker ?? selectedTicker;
                  return t ? (prices[t]?.price ?? fallbackPrices[t] ?? null) : null;
                })()}
                cash={portfolio ? totals.cash : null}
                onTrade={trade}
              />
            </div>
            <div className="grid min-h-0 gap-px bg-line md:grid-cols-2">
              <div className="min-h-0 bg-panel max-lg:h-[260px]">
                <Heatmap positions={positions} onSelect={select} />
              </div>
              <div className="min-h-0 bg-panel max-lg:h-[260px]">
                <PnlChart snapshots={snapshots} liveValue={portfolio ? totals.totalValue : null} />
              </div>
            </div>
            <div className="min-h-0 bg-panel max-lg:min-h-[180px]">
              <PositionsTable positions={positions} onSelect={select} />
            </div>
          </div>
        </div>

        <div
          className={`min-h-0 shrink-0 max-lg:h-[520px] ${chatCollapsed ? "lg:w-10" : "lg:w-[360px] xl:w-[380px]"}`}
        >
          <ChatPanel
            loadHistory={api.getChatHistory}
            send={api.chat}
            onActions={onChatActions}
            collapsed={chatCollapsed}
            onToggle={() => setChatCollapsed((c) => !c)}
          />
        </div>
      </div>
    </div>
  );
}
