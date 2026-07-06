import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter } from "react-router"
import { beforeAll, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { ResetPasswordPage } from "@/features/auth/pages/reset-password-page"
import * as authService from "@/services/auth-service"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

function renderPage(initialEntry: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <ResetPasswordPage />
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  )
}

describe("ResetPasswordPage", () => {
  it("mostra o formulário quando há um token na URL", () => {
    renderPage("/reset-password?token=token-abc")

    expect(screen.getByLabelText(/^nova senha$/i)).toBeInTheDocument()
  })

  it("mostra mensagem de link inválido quando não há token na URL", () => {
    renderPage("/reset-password")

    expect(screen.getByText(/link de recuperação inválido/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/nova senha/i)).not.toBeInTheDocument()
  })

  it("mostra a mensagem de sucesso e o link de login após trocar a senha", async () => {
    vi.spyOn(authService, "resetPassword").mockResolvedValue({ status: "ok" })
    renderPage("/reset-password?token=token-abc")

    await userEvent.type(screen.getByLabelText(/^nova senha$/i), "senha-nova-123")
    await userEvent.type(screen.getByLabelText(/confirmar nova senha/i), "senha-nova-123")
    await userEvent.click(screen.getByRole("button", { name: /salvar nova senha/i }))

    expect(await screen.findByText(/senha alterada com sucesso/i)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /ir para o login/i })).toHaveAttribute("href", "/login")
  })
})
