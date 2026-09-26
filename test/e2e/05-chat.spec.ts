import { test, expect } from "@playwright/test";
import { flattenPosition, getPosition, openApp, waitForPrice } from "./helpers";

// These tests rely on LLM_MOCK=true (see planning/TEAM_CONTRACTS.md "Mock rules").

test.describe("AI chat (mocked LLM)", () => {
  test("generic message gets the deterministic mock response", async ({ page }) => {
    await openApp(page);
    await expect(page.getByTestId("chat-panel")).toBeVisible();

    const assistant = page.locator('[data-testid="chat-message"][data-role="assistant"]');
    const beforeCount = await assistant.count();

    await page.getByTestId("chat-input").fill("How is my portfolio doing?");
    await page.getByTestId("chat-send-button").click();

    await expect(page.locator('[data-testid="chat-message"][data-role="user"]').last()).toContainText(
      "How is my portfolio doing?",
    );
    await expect(assistant).toHaveCount(beforeCount + 1, { timeout: 20_000 });
    await expect(assistant.last()).toContainText("Mock response");
    await expect(page.getByTestId("chat-loading")).toHaveCount(0);
  });

  test("'buy 1 AAPL' executes a trade shown inline and in positions", async ({ page, request }) => {
    await waitForPrice(request, "AAPL");
    await flattenPosition(request, "AAPL");

    await openApp(page);
    await expect(page.getByTestId("position-row-AAPL")).toHaveCount(0);

    const assistant = page.locator('[data-testid="chat-message"][data-role="assistant"]');
    const beforeCount = await assistant.count();
    const actionsBefore = await page.getByTestId("chat-action").count();

    await page.getByTestId("chat-input").fill("buy 1 AAPL");
    await page.getByTestId("chat-send-button").click();

    await expect(assistant).toHaveCount(beforeCount + 1, { timeout: 20_000 });
    const actions = page.getByTestId("chat-action");
    await expect(actions).toHaveCount(actionsBefore + 1);
    await expect(actions.last()).toContainText("AAPL");

    await expect(page.getByTestId("position-row-AAPL")).toBeVisible();
    expect((await getPosition(request, "AAPL"))?.quantity).toBe(1);
  });

  test("chat history is restored after reload", async ({ page }) => {
    await openApp(page);
    const marker = `history check ${Date.now()}`;
    await page.getByTestId("chat-input").fill(marker);
    await page.getByTestId("chat-send-button").click();
    await expect(page.locator('[data-testid="chat-message"][data-role="user"]').last()).toContainText(marker);

    await page.reload();
    await expect(page.getByTestId("chat-message").filter({ hasText: marker })).toHaveCount(1, { timeout: 15_000 });
  });
});
