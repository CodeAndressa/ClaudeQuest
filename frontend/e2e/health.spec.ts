import { expect, test } from "@playwright/test"

test("carrega a página inicial e mostra o status da plataforma", async ({ page }) => {
  await page.goto("/")

  await expect(page).toHaveTitle("ClaudeQuest")
  await expect(page.getByRole("heading", { name: /status da plataforma/i })).toBeVisible()
})
