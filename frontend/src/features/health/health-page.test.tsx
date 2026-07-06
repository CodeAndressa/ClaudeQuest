import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { HealthPage } from "@/features/health/health-page"
import * as healthService from "@/services/health-service"
import * as authService from "@/services/auth-service"
import { useAuthStore } from "@/store/auth-store"

beforeAll(async () => {
  // fixa o idioma nos testes para não depender do idioma do ambiente que roda a suíte
  await i18n.changeLanguage("pt-BR")
})

beforeEach(() => {
  useAuthStore.setState({
    user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
    accessToken: "token-abc",
    isAuthenticated: true,
    isBootstrapping: false,
  })
})

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<HealthPage />} />
            <Route path="/login" element={<div>Tela de login</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  )
}

describe("HealthPage", () => {
  it("mostra o estado de carregamento antes da resposta chegar", () => {
    vi.spyOn(healthService, "fetchHealth").mockReturnValue(new Promise(() => {}))

    renderWithProviders()

    expect(screen.getByRole("status")).toHaveTextContent(/verificando/i)
  })

  it("mostra o ambiente retornado quando o backend responde com sucesso", async () => {
    vi.spyOn(healthService, "fetchHealth").mockResolvedValue({
      app: "ClaudeQuest",
      environment: "development",
      status: "ok",
    })

    renderWithProviders()

    await waitFor(() => {
      expect(screen.getByText(/development/i)).toBeInTheDocument()
    })
  })

  it("mostra o estado de erro e permite tentar novamente quando o backend falha", async () => {
    vi.spyOn(healthService, "fetchHealth").mockRejectedValue(new Error("network down"))

    renderWithProviders()

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument()
    })

    const fetchHealthSpy = vi.spyOn(healthService, "fetchHealth")
    await userEvent.click(screen.getByRole("button", { name: /tentar novamente/i }))

    expect(fetchHealthSpy).toHaveBeenCalled()
  })

  it("faz logout, limpa a sessão e navega para /login ao clicar em Sair", async () => {
    vi.spyOn(healthService, "fetchHealth").mockResolvedValue({
      app: "ClaudeQuest",
      environment: "development",
      status: "ok",
    })
    const logoutSpy = vi.spyOn(authService, "logout").mockResolvedValue({ status: "ok" })

    renderWithProviders()

    await userEvent.click(screen.getByRole("button", { name: /sair/i }))

    await waitFor(() => expect(screen.getByText(/tela de login/i)).toBeInTheDocument())
    expect(logoutSpy).toHaveBeenCalled()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("limpa a sessão e navega para /login mesmo se a chamada de logout falhar", async () => {
    vi.spyOn(healthService, "fetchHealth").mockResolvedValue({
      app: "ClaudeQuest",
      environment: "development",
      status: "ok",
    })
    vi.spyOn(authService, "logout").mockRejectedValue(new Error("network down"))

    renderWithProviders()

    await userEvent.click(screen.getByRole("button", { name: /sair/i }))

    await waitFor(() => expect(screen.getByText(/tela de login/i)).toBeInTheDocument())
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})
