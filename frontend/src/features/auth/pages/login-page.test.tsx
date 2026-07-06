import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { LoginPage } from "@/features/auth/pages/login-page"
import * as authService from "@/services/auth-service"
import { useAuthStore } from "@/store/auth-store"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

beforeEach(() => {
  useAuthStore.getState().clearSession()
})

function renderLoginPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/login"]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<div>Página inicial</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  )
}

describe("LoginPage", () => {
  it("renderiza o título e o formulário de login", () => {
    renderLoginPage()

    expect(screen.getByRole("heading", { name: /entrar no claudequest/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument()
  })

  it("navega para a página inicial após um login bem-sucedido", async () => {
    vi.spyOn(authService, "login").mockResolvedValue({
      access_token: "token-abc",
      refresh_token: "refresh-abc",
      token_type: "bearer",
      expires_in: 1800,
      user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
    })
    renderLoginPage()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "senha-correta")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    await waitFor(() => expect(screen.getByText(/página inicial/i)).toBeInTheDocument())
  })
})
