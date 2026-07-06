import { expect, test } from "@playwright/test"

test("carrega a página inicial e mostra o status da plataforma para um usuário logado", async ({
  page,
}) => {
  await page.goto("/login")
  await page.getByLabel(/e-mail/i).fill("admin@claudequest.dev")
  await page.getByLabel(/senha/i).fill("ClaudeQuest#2026")
  await page.getByRole("button", { name: /entrar/i }).click()

  await expect(page).toHaveURL("/")
  await expect(page).toHaveTitle("ClaudeQuest")
  await expect(page.getByRole("heading", { name: /status da plataforma/i })).toBeVisible()
})

test("redireciona visitantes não autenticados de / para /login", async ({ page }) => {
  await page.goto("/")

  await expect(page).toHaveURL("/login")
})
