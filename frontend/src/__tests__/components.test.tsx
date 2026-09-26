import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";
import Watchlist, { buildWatchlistRows, type WatchlistRowData } from "@/components/Watchlist";
import Header from "@/components/Header";
import PositionsTable from "@/components/PositionsTable";
import Heatmap from "@/components/Heatmap";
import TradeBar from "@/components/TradeBar";
import ChatPanel from "@/components/ChatPanel";
import { FLASH_MS } from "@/components/useFlash";
import type { ChatMessage, ChatResponse, Position } from "@/lib/types";

const row = (ticker: string, price: number | null): WatchlistRowData => ({
  ticker,
  price,
  changePercent: 0.5,
  points: [],
});

describe("Watchlist", () => {
  it("renders rows with prices and required test ids", () => {
    render(
      <Watchlist
        rows={[row("AAPL", 190.5), row("MSFT", null)]}
        selected="AAPL"
        onSelect={() => {}}
        onAdd={async () => {}}
        onRemove={async () => {}}
      />,
    );
    expect(screen.getByTestId("watchlist")).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveTextContent("190.50");
    expect(screen.getByTestId("watchlist-price-MSFT")).toHaveTextContent("—");
    expect(screen.getByTestId("watchlist-row-AAPL")).toHaveAttribute("aria-selected", "true");
  });

  describe("price flash", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it("applies an up/down flash class on change and removes it afterwards", () => {
      const props = { selected: null, onSelect: () => {}, onAdd: async () => {}, onRemove: async () => {} };
      const { rerender } = render(<Watchlist rows={[row("AAPL", 190)]} {...props} />);
      const cell = screen.getByTestId("watchlist-price-AAPL");
      expect(cell.className).not.toMatch(/flash-(up|down)/);

      rerender(<Watchlist rows={[row("AAPL", 191)]} {...props} />);
      expect(cell).toHaveClass("flash-up");
      act(() => {
        vi.advanceTimersByTime(FLASH_MS + 10);
      });
      expect(cell).not.toHaveClass("flash-up");

      rerender(<Watchlist rows={[row("AAPL", 189)]} {...props} />);
      expect(cell).toHaveClass("flash-down");
    });
  });

  it("adds a ticker (upper-cased) and removes one", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [tickers, setTickers] = useState(["AAPL"]);
      return (
        <Watchlist
          rows={tickers.map((t) => row(t, 100))}
          selected={null}
          onSelect={() => {}}
          onAdd={async (t) => setTickers((c) => [...c, t])}
          onRemove={async (t) => setTickers((c) => c.filter((x) => x !== t))}
        />
      );
    }
    render(<Harness />);
    await user.type(screen.getByTestId("watchlist-add-input"), "pypl");
    await user.click(screen.getByTestId("watchlist-add-button"));
    expect(await screen.findByTestId("watchlist-row-PYPL")).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-add-input")).toHaveValue("");

    await user.click(screen.getByTestId("watchlist-remove-AAPL"));
    await waitFor(() => expect(screen.queryByTestId("watchlist-row-AAPL")).not.toBeInTheDocument());
  });

  it("shows the server error when adding fails", async () => {
    const user = userEvent.setup();
    render(
      <Watchlist
        rows={[]}
        selected={null}
        onSelect={() => {}}
        onAdd={async () => {
          throw new Error("AAPL is already in the watchlist");
        }}
        onRemove={async () => {}}
      />,
    );
    await user.type(screen.getByTestId("watchlist-add-input"), "AAPL");
    await user.click(screen.getByTestId("watchlist-add-button"));
    expect(await screen.findByRole("alert")).toHaveTextContent("already in the watchlist");
  });

  it("builds rows from stream prices with API fallback and session change", () => {
    const rows = buildWatchlistRows(
      ["AAPL", "MSFT"],
      {
        AAPL: {
          ticker: "AAPL",
          price: 110,
          previous_price: 109,
          timestamp: 1,
          change: 1,
          change_percent: 1,
          direction: "up",
        },
      },
      {},
      { AAPL: 100 },
      { MSFT: 400 },
    );
    expect(rows[0].price).toBe(110);
    expect(rows[0].changePercent).toBeCloseTo(10);
    expect(rows[1].price).toBe(400);
    expect(rows[1].changePercent).toBeNull();
  });
});

describe("Header", () => {
  it("shows totals and connection status", () => {
    render(<Header totalValue={10234.5} cash={8000} unrealizedPnl={34.5} startingValue={10000} status="connected" />);
    expect(screen.getByTestId("header-total-value")).toHaveTextContent("$10,234.50");
    expect(screen.getByTestId("header-cash")).toHaveTextContent("$8,000.00");
    expect(screen.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
  });

  it("reflects reconnecting status", () => {
    render(<Header totalValue={null} cash={null} unrealizedPnl={null} startingValue={10000} status="reconnecting" />);
    expect(screen.getByTestId("connection-status")).toHaveAttribute("data-status", "reconnecting");
  });
});

const positions: Position[] = [
  { ticker: "AAPL", quantity: 10, avg_cost: 100, current_price: 110, market_value: 1100, unrealized_pnl: 100, pnl_percent: 10 },
  { ticker: "TSLA", quantity: 1.5, avg_cost: 200, current_price: 180, market_value: 270, unrealized_pnl: -30, pnl_percent: -10 },
];

describe("PositionsTable", () => {
  it("renders a row per position with P&L", () => {
    render(<PositionsTable positions={positions} />);
    const aapl = screen.getByTestId("position-row-AAPL");
    expect(within(aapl).getByText("+$100.00")).toHaveClass("text-up");
    expect(within(aapl).getByText("+10.00%")).toBeInTheDocument();
    const tsla = screen.getByTestId("position-row-TSLA");
    expect(within(tsla).getByText("1.5")).toBeInTheDocument();
    expect(within(tsla).getByText("-$30.00")).toHaveClass("text-down");
  });

  it("shows an empty state", () => {
    render(<PositionsTable positions={[]} />);
    expect(screen.getByTestId("positions-table")).toHaveTextContent("No open positions");
  });
});

describe("Heatmap", () => {
  it("renders a tile per position colored by P&L", () => {
    render(<Heatmap positions={positions} />);
    const heat = screen.getByTestId("heatmap");
    expect(heat).toHaveTextContent("AAPL");
    expect(heat).toHaveTextContent("TSLA");
    expect(screen.getByTestId("heatmap-tile-AAPL").style.backgroundColor).toContain("47, 191, 113");
    expect(screen.getByTestId("heatmap-tile-TSLA").style.backgroundColor).toContain("239, 90, 90");
  });
});

describe("TradeBar", () => {
  it("submits buy and sell orders and shows errors", async () => {
    const user = userEvent.setup();
    const onTrade = vi
      .fn()
      .mockResolvedValueOnce({ id: "1", ticker: "AAPL", side: "buy", quantity: 5, price: 190, executed_at: "" })
      .mockRejectedValueOnce(new Error("Insufficient shares"));
    render(<TradeBar ticker="AAPL" onTickerChange={() => {}} price={190} cash={10000} onTrade={onTrade} />);
    await user.type(screen.getByTestId("trade-quantity-input"), "5");
    await user.click(screen.getByTestId("trade-buy-button"));
    expect(onTrade).toHaveBeenCalledWith("AAPL", 5, "buy");
    expect(await screen.findByText(/Bought 5 AAPL/)).toBeInTheDocument();

    await user.click(screen.getByTestId("trade-sell-button"));
    expect(onTrade).toHaveBeenLastCalledWith("AAPL", 5, "sell");
    expect(await screen.findByTestId("trade-error")).toHaveTextContent("Insufficient shares");
  });

  it("validates quantity before calling the API", async () => {
    const user = userEvent.setup();
    const onTrade = vi.fn();
    render(<TradeBar ticker="AAPL" onTickerChange={() => {}} price={190} cash={10000} onTrade={onTrade} />);
    await user.click(screen.getByTestId("trade-buy-button"));
    expect(onTrade).not.toHaveBeenCalled();
    expect(screen.getByTestId("trade-error")).toHaveTextContent("quantity");
  });
});

describe("ChatPanel", () => {
  const history: ChatMessage[] = [
    { id: "a", role: "user", content: "hello", actions: null, created_at: "" },
    {
      id: "b",
      role: "assistant",
      content: "Bought it",
      actions: {
        trades: [{ ticker: "NVDA", side: "buy", quantity: 2, status: "executed", price: 800, error: null }],
        watchlist_changes: [],
      },
      created_at: "",
    },
  ];

  it("restores history with inline actions", async () => {
    render(
      <ChatPanel
        loadHistory={async () => ({ messages: history })}
        send={vi.fn()}
        collapsed={false}
        onToggle={() => {}}
      />,
    );
    const msgs = await screen.findAllByTestId("chat-message");
    expect(msgs).toHaveLength(2);
    expect(msgs[0]).toHaveAttribute("data-role", "user");
    expect(msgs[1]).toHaveAttribute("data-role", "assistant");
    expect(screen.getByTestId("chat-action")).toHaveTextContent("Bought 2 NVDA at 800.00");
  });

  it("shows loading while waiting and renders the reply with actions", async () => {
    const user = userEvent.setup();
    let resolve!: (r: ChatResponse) => void;
    const send = vi.fn(() => new Promise<ChatResponse>((r) => (resolve = r)));
    const onActions = vi.fn();
    render(
      <ChatPanel
        loadHistory={async () => ({ messages: [] })}
        send={send}
        onActions={onActions}
        collapsed={false}
        onToggle={() => {}}
      />,
    );
    await user.type(screen.getByTestId("chat-input"), "buy 5 AAPL");
    await user.click(screen.getByTestId("chat-send-button"));
    expect(send).toHaveBeenCalledWith("buy 5 AAPL");
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
    expect(screen.getByTestId("chat-message")).toHaveAttribute("data-role", "user");

    await act(async () => {
      resolve({
        message: "Done.",
        trades: [
          { ticker: "AAPL", side: "buy", quantity: 5, status: "executed", price: 190, error: null },
          { ticker: "TSLA", side: "sell", quantity: 1, status: "failed", error: "Insufficient shares" },
        ],
        watchlist_changes: [{ ticker: "PYPL", action: "add", status: "executed", error: null }],
      });
    });
    expect(screen.queryByTestId("chat-loading")).not.toBeInTheDocument();
    const actions = screen.getAllByTestId("chat-action");
    expect(actions).toHaveLength(2);
    expect(actions[0]).toHaveTextContent("AAPL");
    expect(actions[1]).toHaveTextContent("PYPL");
    expect(screen.getByTestId("chat-action-failed")).toHaveTextContent("Insufficient shares");
    expect(onActions).toHaveBeenCalledTimes(1);
  });

  it("collapses to a rail", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <ChatPanel loadHistory={async () => ({ messages: [] })} send={vi.fn()} collapsed onToggle={onToggle} />,
    );
    expect(screen.getByTestId("chat-panel")).toHaveAttribute("data-collapsed", "true");
    expect(screen.queryByTestId("chat-input")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open finally chat/i }));
    expect(onToggle).toHaveBeenCalled();
  });
});
