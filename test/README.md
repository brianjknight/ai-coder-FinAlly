# FinAlly E2E Tests

Playwright (TypeScript) end-to-end and API contract tests. Standalone npm project;
`@playwright/test` is pinned to `1.63.0` to match the `mcr.microsoft.com/playwright:v1.63.0-noble` image.

## Layout

| File | Covers |
|---|---|
| `e2e/01-fresh-start.spec.ts` | Default 10-ticker watchlist, header cash/total, connection status, prices streaming, ticker selection |
| `e2e/02-watchlist.spec.ts` | Add/remove a ticker via the UI, persistence across reload |
| `e2e/03-trading.spec.ts` | Buy (cash down, position row appears), sell (cash up, position updates/disappears), trade errors |
| `e2e/04-portfolio-viz.spec.ts` | Heatmap, P&L chart, main chart render |
| `e2e/05-chat.spec.ts` | Mocked AI chat: generic reply, `buy 1 AAPL` executes with inline `chat-action`, history restore |
| `e2e/06-sse-resilience.spec.ts` | Network drop -> status leaves `connected` -> reconnects and prices resume |
| `e2e/api.spec.ts` | REST + SSE contract (`planning/TEAM_CONTRACTS.md`) |

The UI tests rely on the `data-testid`s listed in `planning/TEAM_CONTRACTS.md`, and chat tests rely on
`LLM_MOCK=true`. Tests run serially (one shared DB) and use relative assertions, so they can be run
repeatedly against a non-fresh database. Strict "fresh start" checks (exactly $10,000 cash, no positions,
exact default watchlist) only run when `FRESH_DB=1`.

## Option A: Docker (recommended, fresh DB every run)

```bash
cd test
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
docker compose -f docker-compose.test.yml down -v
```

The HTML report is written to `test/playwright-report/` (open with `npx playwright show-report`).

## Option B: Against a locally running app

Start the app with the mock LLM (from the repo root):

```bash
cd frontend && npm ci && npm run build && cd ..
rm -rf backend/static && cp -r frontend/out backend/static
cd backend && LLM_MOCK=true DB_PATH=/tmp/finally-e2e.db uv run uvicorn app.main:app --port 8000
```

Then in another shell:

```bash
cd test
npm install
npx playwright install chromium
npx playwright test                 # all tests
npx playwright test e2e/api.spec.ts # API only
FRESH_DB=1 npx playwright test      # only if the DB was just created
BASE_URL=http://localhost:8001 npx playwright test   # different target
```

Or run against the production container started by `scripts/start_*` (needs `LLM_MOCK=true` in `.env`
for the chat tests to pass).
