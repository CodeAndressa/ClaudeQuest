import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter } from "react-router"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { LoginForm } from "@/features/auth/components/login-form"
import * as authService from "@/services/auth-service"
import { ApiError } from "@/types/api"
import { useAuthStore } from "@/store/auth-store"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

beforeEach(() => {
  useAuthStore.getState().clearSession()
})

function renderForm(onSuccess = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LoginForm onSuccess={onSuccess} />
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  )
  return { onSuccess }
}

describe("LoginForm", () => {
  it("mostra erros de validação ao submeter vazio", async () => {
    renderForm()

    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    expect(await screen.findAllByRole("alert")).not.toHaveLength(0)
    expect(screen.getByText(/e-mail válido/i)).toBeInTheDocument()
  })

  it("faz login com sucesso e chama onSuccess salvando a sessão", async () => {
    vi.spyOn(authService, "login").mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_in: 1800,
      user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
    })
    const { onSuccess } = renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "senha-correta")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(useAuthStore.getState().accessToken).toBe("token-abc")
  })

  it("mostra mensagem de credenciais inválidas quando o backend rejeita", async () => {
    vi.spyOn(authService, "login").mockRejectedValue(
      new ApiError({
        success: false,
        error: { code: "invalid_credentials", message: "x", details: {} },
        trace_id: "t1",
        timestamp: "2026-01-01T00:00:00Z",
      })
    )
    renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "senha-errada")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    expect(await screen.findByText(/e-mail ou senha inválidos/i)).toBeInTheDocument()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it("mostra mensagem genérica para erros inesperados", async () => {
    vi.spyOn(authService, "login").mockRejectedValue(new Error("network down"))
    renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "qualquer")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    expect(await screen.findByText(/não foi possível entrar agora/i)).toBeInTheDocument()
  })

  it("mostra mensagem genérica para códigos de erro da API não mapeados", async () => {
    vi.spyOn(authService, "login").mockRejectedValue(
      new ApiError({
        success: false,
        error: { code: "database_unavailable", message: "x", details: {} },
        trace_id: "t2",
        timestamp: "2026-01-01T00:00:00Z",
      })
    )
    renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "qualquer")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    expect(await screen.findByText(/não foi possível entrar agora/i)).toBeInTheDocument()
  })

  it("desabilita o botão e mostra o spinner enquanto a requisição está pendente", async () => {
    vi.spyOn(authService, "login").mockReturnValue(new Promise(() => {}))
    renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "senha-correta")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    expect(await screen.findByRole("button", { name: /entrar/i })).toBeDisabled()
  })
})
