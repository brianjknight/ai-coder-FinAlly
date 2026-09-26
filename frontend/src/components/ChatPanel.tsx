"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { ChatActions, ChatMessage, ChatResponse } from "@/lib/types";
import { formatPrice, formatQty } from "@/lib/format";

export interface ChatPanelProps {
  loadHistory: () => Promise<{ messages: ChatMessage[] }>;
  send: (message: string) => Promise<ChatResponse>;
  /** Called after an assistant reply that executed trades or watchlist changes. */
  onActions?: (actions: ChatActions) => void;
  collapsed: boolean;
  onToggle: () => void;
}

const SUGGESTIONS = ["How is my portfolio doing?", "Buy 5 AAPL", "Add PYPL to my watchlist"];

function hasActions(a: ChatActions | null | undefined): boolean {
  return !!a && ((a.trades?.length ?? 0) > 0 || (a.watchlist_changes?.length ?? 0) > 0);
}

export function ActionList({ actions }: { actions: ChatActions | null | undefined }) {
  if (!actions || !hasActions(actions)) return null;
  return (
    <ul className="mt-2 space-y-1">
      {(actions.trades ?? []).map((t, i) => {
        const ok = t.status === "executed";
        return (
          <li
            key={`t-${i}`}
            data-testid={ok ? "chat-action" : "chat-action-failed"}
            data-status={t.status}
            className={`num flex items-start gap-2 rounded border px-2 py-1 text-xs ${
              ok ? "border-up/40 bg-up/10 text-text" : "border-down/40 bg-down/10 text-text"
            }`}
          >
            <span className={ok ? "text-up" : "text-down"} aria-hidden="true">
              {ok ? "✓" : "✕"}
            </span>
            <span>
              {ok ? (t.side === "buy" ? "Bought" : "Sold") : `${t.side === "buy" ? "Buy" : "Sell"} failed:`}{" "}
              {formatQty(t.quantity)} {t.ticker}
              {ok && t.price != null ? ` at ${formatPrice(t.price)}` : ""}
              {!ok && t.error ? ` (${t.error})` : ""}
            </span>
          </li>
        );
      })}
      {(actions.watchlist_changes ?? []).map((w, i) => {
        const ok = w.status === "executed";
        return (
          <li
            key={`w-${i}`}
            data-testid={ok ? "chat-action" : "chat-action-failed"}
            data-status={w.status}
            className={`num flex items-start gap-2 rounded border px-2 py-1 text-xs ${
              ok ? "border-blue/40 bg-blue/10 text-text" : "border-down/40 bg-down/10 text-text"
            }`}
          >
            <span className={ok ? "text-blue" : "text-down"} aria-hidden="true">
              {ok ? (w.action === "add" ? "+" : "−") : "✕"}
            </span>
            <span>
              {ok
                ? `${w.action === "add" ? "Added" : "Removed"} ${w.ticker} ${w.action === "add" ? "to" : "from"} watchlist`
                : `Watchlist ${w.action} failed for ${w.ticker}${w.error ? ` (${w.error})` : ""}`}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function MessageBubble({ m }: { m: ChatMessage }) {
  const user = m.role === "user";
  return (
    <div data-testid="chat-message" data-role={m.role} className={`flex ${user ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[92%] rounded-md px-3 py-2 text-[13px] leading-relaxed ${
          user ? "bg-blue/15 text-text" : "border border-line bg-raised text-text"
        }`}
      >
        {!user && <div className="mb-0.5 text-[11px] font-semibold text-accent">FinAlly</div>}
        <p className="whitespace-pre-wrap break-words">{m.content}</p>
        {!user && <ActionList actions={m.actions} />}
      </div>
    </div>
  );
}

let localId = 0;
const nextId = () => `local-${Date.now()}-${++localId}`;

export default function ChatPanel({ loadHistory, send, onActions, collapsed, onToggle }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let cancelled = false;
    loadHistory()
      .then((res) => {
        if (!cancelled && Array.isArray(res?.messages)) {
          // Keep any messages sent before history arrived.
          setMessages((cur) => [...res.messages, ...cur]);
        }
      })
      .catch(() => {
        /* history is best-effort */
      });
    return () => {
      cancelled = true;
    };
  }, [loadHistory]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading, collapsed]);

  const submit = async (text: string) => {
    const message = text.trim();
    if (!message || loading) return;
    setError(null);
    setInput("");
    setMessages((cur) => [
      ...cur,
      { id: nextId(), role: "user", content: message, actions: null, created_at: new Date().toISOString() },
    ]);
    setLoading(true);
    try {
      const res = await send(message);
      const actions: ChatActions = { trades: res.trades ?? [], watchlist_changes: res.watchlist_changes ?? [] };
      setMessages((cur) => [
        ...cur,
        {
          id: nextId(),
          role: "assistant",
          content: res.message,
          actions: hasActions(actions) ? actions : null,
          created_at: new Date().toISOString(),
        },
      ]);
      if (hasActions(actions)) onActions?.(actions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "FinAlly could not respond. Try again.");
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void submit(input);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit(input);
    }
  };

  if (collapsed) {
    return (
      <aside
        data-testid="chat-panel"
        data-collapsed="true"
        aria-label="AI assistant"
        className="flex h-full w-10 flex-col items-center border-l border-line bg-panel py-3"
      >
        <button
          type="button"
          onClick={onToggle}
          aria-label="Open FinAlly chat"
          aria-expanded={false}
          className="rounded px-1 py-2 text-xs font-semibold text-accent [writing-mode:vertical-rl] hover:bg-raised"
        >
          Ask FinAlly
        </button>
      </aside>
    );
  }

  return (
    <aside
      data-testid="chat-panel"
      data-collapsed="false"
      aria-label="AI assistant"
      className="flex h-full min-h-0 w-full flex-col border-l border-line bg-panel"
    >
      <div className="flex items-center justify-between border-b border-line px-3 py-2.5">
        <div>
          <h2 className="text-[13px] font-semibold text-text">FinAlly</h2>
          <p className="text-[11px] text-muted">Analyzes your book and trades on request</p>
        </div>
        <button
          type="button"
          onClick={onToggle}
          aria-label="Collapse chat"
          aria-expanded={true}
          className="rounded px-2 py-1 text-muted hover:bg-raised hover:text-text"
        >
          ⟩
        </button>
      </div>

      <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 space-y-2.5 overflow-y-auto px-3 py-3" aria-live="polite">
        {messages.length === 0 && !loading && (
          <div className="space-y-2 pt-2 text-[13px] text-muted">
            <p>Ask about risk, concentration or P&amp;L, or tell FinAlly what to trade.</p>
            <div className="flex flex-wrap gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void submit(s)}
                  className="rounded border border-line px-2 py-1 text-xs text-text hover:border-accent/60 hover:text-accent"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} m={m} />
        ))}
        {loading && (
          <div data-testid="chat-loading" role="status" className="flex items-center gap-2 text-xs text-muted">
            <span className="chat-dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            FinAlly is thinking
          </div>
        )}
        {error && (
          <p role="alert" data-testid="chat-error" className="text-xs text-down">
            {error}
          </p>
        )}
      </div>

      <form onSubmit={onSubmit} className="border-t border-line p-2.5">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            data-testid="chat-input"
            aria-label="Message FinAlly"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask FinAlly…"
            className="scroll-thin min-h-[40px] flex-1 resize-none rounded border border-line bg-ink px-2 py-1.5 text-[13px] text-text placeholder:text-dim focus:border-blue focus:outline-none"
          />
          <button
            type="submit"
            data-testid="chat-send-button"
            disabled={loading || !input.trim()}
            className="rounded bg-purple px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-purple-hi disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </aside>
  );
}
