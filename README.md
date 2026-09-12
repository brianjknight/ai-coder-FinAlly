# FinAlly — the Finance Ally

A visually stunning AI-powered trading workstation: live-streaming market data, a simulated portfolio, and an LLM copilot that can analyze positions and execute trades on your behalf. Think Bloomberg terminal meets AI copilot.

This is the capstone project for an agentic AI coding course — built entirely by orchestrated Coding Agents from a shared spec.

> **Status:** In planning. The full specification lives in [`planning/PLAN.md`](planning/PLAN.md); implementation has not started yet.

## Highlights (per spec)

- Live watchlist of 10 default tickers streamed over SSE, with sparklines and flash animations
- $10,000 simulated cash, market-order-only buy/sell with instant fills
- Portfolio heatmap, P&L chart, and positions table
- AI chat assistant (via LiteLLM → OpenRouter, Cerebras inference) that can analyze your portfolio and execute trades or watchlist changes through natural language
- Single Docker container, single port (`8000`), SQLite storage — one command to run

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js (TypeScript), static export |
| Backend | FastAPI (Python), managed with `uv` |
| Database | SQLite (bind-mounted at `db/finally.db`) |
| Real-time data | Server-Sent Events |
| AI | LiteLLM → OpenRouter (`openrouter/openai/gpt-oss-120b` via Cerebras) |
| Market data | Built-in simulator by default; Massive (Polygon.io) API optional |

## Getting Started

Not yet runnable — see [`planning/PLAN.md`](planning/PLAN.md) for the full design, directory layout, environment variables, API surface, and testing strategy. Once built, the intended flow is:

```bash
cp .env.example .env   # add your OPENROUTER_API_KEY
./scripts/start_mac.sh # or scripts/start_windows.ps1
```

then open `http://localhost:8000`.

## Documentation

All project documentation lives in [`planning/`](planning/). [`PLAN.md`](planning/PLAN.md) is the canonical, single source of truth referenced by every agent working on this project.

## License

See [`LICENSE`](LICENSE).
