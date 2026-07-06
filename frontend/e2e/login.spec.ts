import { expect, test } from "@playwright/test"

test.describe("Login", () => {
  test("mostra erro ao tentar entrar com credenciais inválidas", async ({ page }) => {
    await page.goto("/login")

    await page.getByLabel(/e-mail/i).fill("admin@claudequest.dev")
    await page.getByLabel(/senha/i).fill("senha-errada")
    await page.getByRole("button", { name: /entrar/i }).click()

    await expect(page.getByText(/e-mail ou senha inválidos/i)).toBeVisible()
  })

  test("entra com sucesso usando o admin de demonstração e é redirecionado", async ({ page }) => {
    await page.goto("/login")

    await page.getByLabel(/e-mail/i).fill("admin@claudequest.dev")
    await page.getByLabel(/senha/i).fill("ClaudeQuest#2026")
    await page.getByRole("button", { name: /entrar/i }).click()

    await expect(page).toHaveURL("/")
    await expect(page.getByRole("heading", { name: /status da plataforma/i })).toBeVisible()
  })
})
