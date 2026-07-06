import { expect, test } from "@playwright/test"

test.describe("Recuperação de senha", () => {
  test("permite navegar do login até o pedido de recuperação e ver a confirmação", async ({
    page,
  }) => {
    await page.goto("/login")

    await page.getByRole("link", { name: /esqueci minha senha/i }).click()
    await expect(page).toHaveURL("/forgot-password")

    await page.getByLabel(/e-mail/i).fill("admin@claudequest.dev")
    await page.getByRole("button", { name: /enviar link de recuperação/i }).click()

    await expect(page.getByText(/você vai receber um link/i)).toBeVisible()
  })

  test("mostra link inválido na tela de reset sem token na URL", async ({ page }) => {
    await page.goto("/reset-password")

    await expect(page.getByText(/link de recuperação inválido/i)).toBeVisible()
  })
})
