# FinAlly — AI Trading Workstation

A visually stunning AI-powered trading workstation that streams live market data, simulates portfolio trading, and integrates an LLM chat assistant that can analyze positions and execute trades via natural language.

Built entirely by coding agents as a capstone project for an agentic AI coding course.

## Features

- **Live price streaming** via SSE with green/red flash animations
- **Simulated portfolio** — $10k virtual cash, market orders, instant fills
- **Portfolio visualizations** — heatmap (treemap), P&L chart, positions table
- **AI chat assistant** — analyzes holdings, suggests and auto-executes trades
- **Watchlist management** — track tickers manually or via AI
- **Dark terminal aesthetic** — Bloomberg-inspired, data-dense layout

## Architecture

Single Docker container serving everything on port 8000:

- **Frontend**: Next.js (static export) with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python/uv) with SSE streaming
- **Database**: SQLite with lazy initialization
- **AI**: LiteLLM → OpenRouter (Cerebras inference) with structured outputs
- **Market data**: Built-in GBM simulator (default) or Massive API (optional)

## Quick Start

Requires Docker. First configure your environment:

```bash
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env (or set LLM_MOCK=true to run without one)
```

Then start the app with the script for your platform (builds the image on first run):

```bash
# macOS / Linux
./scripts/start_mac.sh            # add --build to force a rebuild, --no-open to skip the browser
./scripts/stop_mac.sh
```

```powershell
# Windows PowerShell
.\scripts\start_windows.ps1       # add -Build to force a rebuild, -NoOpen to skip the browser
.\scripts\stop_windows.ps1
```

Open http://localhost:8000. Stopping removes the container but keeps the `finally-data`
volume, so your portfolio persists across restarts (`docker volume rm finally-data` to reset).

Alternatively, run Docker directly or via Compose:

```bash
docker build -t finally .
docker run -d --name finally -v finally-data:/app/db -p 8000:8000 --env-file .env finally
# or
docker compose up -d --build
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for AI chat |
| `MASSIVE_API_KEY` | No | Massive (Polygon.io) key for real market data; omit to use simulator |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses (testing) |

## Project Structure

```
finally/
├── frontend/    # Next.js static export
├── backend/     # FastAPI uv project
├── planning/    # Project documentation and agent contracts
├── test/        # Playwright E2E tests
├── db/          # SQLite volume mount (runtime)
└── scripts/     # Start/stop helpers
```

## License

See [LICENSE](LICENSE).
