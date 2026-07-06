import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { HealthPage } from "@/features/health/health-page"
import * as healthService from "@/services/health-service"

beforeAll(async () => {
  // fixa o idioma nos testes para não depender do idioma do ambiente que roda a suíte
  await i18n.changeLanguage("pt-BR")
})

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <HealthPage />
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
    await userEvent.click(screen.getByRole("button"))

    expect(fetchHealthSpy).toHaveBeenCalled()
  })
})
