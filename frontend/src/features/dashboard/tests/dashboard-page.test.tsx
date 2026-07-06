import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { DashboardPage } from "@/features/dashboard/pages/dashboard-page"
import * as dashboardService from "@/features/dashboard/services/dashboard-service"
import type { DashboardSummary } from "@/features/dashboard/types/dashboard"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <DashboardPage />
      </QueryClientProvider>
    </I18nextProvider>
  )
}

const fullDashboard: DashboardSummary = {
  xp: { total: 120, level: 3, xp_to_next_level: 80 },
  streak: { current_days: 5, last_active_date: "2026-07-05" },
  ranking: { position: 12, total_users: 340 },
  next_lesson: {
    track_title: "Claude Chat",
    lesson_title: "Prompts eficazes",
    lesson_id: "lesson-1",
  },
  badges: [],
  certificates: [],
}

const emptyDashboard: DashboardSummary = {
  xp: { total: 0, level: 1, xp_to_next_level: 100 },
  streak: { current_days: 0, last_active_date: null },
  ranking: { position: null, total_users: 0 },
  next_lesson: null,
  badges: [],
  certificates: [],
}

describe("DashboardPage", () => {
  it("mostra o skeleton de carregamento antes da resposta chegar", () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByRole("status", { name: "" })).toBeInTheDocument()
  })

  it("mostra o estado de erro e permite tentar novamente quando o backend falha", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockRejectedValue(new Error("network down"))

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument()
    })

    const fetchSpy = vi.spyOn(dashboardService, "fetchDashboard")
    await userEvent.click(screen.getByRole("button", { name: /tentar novamente/i }))

    expect(fetchSpy).toHaveBeenCalled()
  })

  it("mostra todos os cards com dados quando o backend responde com sucesso", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(fullDashboard)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("120")).toBeInTheDocument()
    })

    expect(screen.getByText(/nível 3/i)).toBeInTheDocument()
    expect(screen.getByText(/faltam 80 xp/i)).toBeInTheDocument()

    expect(screen.getByText("5")).toBeInTheDocument()
    expect(screen.getByText(/dias consecutivos/i)).toBeInTheDocument()

    expect(screen.getByText("#12")).toBeInTheDocument()
    expect(screen.getByText(/de 340 usuários/i)).toBeInTheDocument()

    expect(screen.getByText("Claude Chat")).toBeInTheDocument()
    expect(screen.getByText("Prompts eficazes")).toBeInTheDocument()

    expect(screen.getAllByText(/em breve/i).length).toBeGreaterThanOrEqual(2)
  })

  it("mostra estado de streak zerado com mensagem de incentivo", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(emptyDashboard)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/comece hoje/i)).toBeInTheDocument()
    })
  })

  it("mostra estado vazio de ranking quando position é null", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(emptyDashboard)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/você ainda não está em nenhum ranking/i)).toBeInTheDocument()
    })
  })

  it("mostra estado vazio de próxima missão quando next_lesson é null", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(emptyDashboard)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/nenhum conteúdo disponível ainda/i)).toBeInTheDocument()
    })
  })

  it("mostra mensagem de em breve ao clicar no botão de começar a próxima missão", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(fullDashboard)

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /começar/i })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole("button", { name: /começar/i }))

    expect(
      screen.getByText(/esta missão ainda não está disponível\. em breve!/i)
    ).toBeInTheDocument()
  })

  it("mostra estados de em breve honestos para badges e certificados, sempre vazios", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(fullDashboard)

    renderPage()

    await waitFor(() => {
      expect(
        screen.getByText(/em breve você poderá conquistar badges por aqui/i)
      ).toBeInTheDocument()
    })

    expect(
      screen.getByText(/em breve você poderá conquistar certificados por aqui/i)
    ).toBeInTheDocument()
  })
})
