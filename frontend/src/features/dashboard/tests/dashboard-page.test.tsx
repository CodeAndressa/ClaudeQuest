import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter } from "react-router"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { DashboardPage } from "@/features/dashboard/pages/dashboard-page"
import * as dashboardService from "@/features/dashboard/services/dashboard-service"
import * as gamificationService from "@/features/dashboard/services/gamification-service"
import type { DashboardSummary } from "@/features/dashboard/types/dashboard"
import type {
  RankingSummary,
  UserBadge,
  UserCertificate,
} from "@/features/dashboard/types/gamification"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

const emptyRanking: RankingSummary = { top: [], current_user: null, total_users: 0 }
const emptyBadges: UserBadge[] = []
const emptyCertificates: UserCertificate[] = []

beforeEach(() => {
  vi.spyOn(gamificationService, "fetchRanking").mockResolvedValue(emptyRanking)
  vi.spyOn(gamificationService, "fetchMyBadges").mockResolvedValue(emptyBadges)
  vi.spyOn(gamificationService, "fetchMyCertificates").mockResolvedValue(emptyCertificates)
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  )
}

const fullDashboard: DashboardSummary = {
  xp: { total: 120, level: 3, xp_to_next_level: 80 },
  streak: { current_days: 5, last_active_date: "2026-07-05" },
  ranking: { position: 12, total_users: 340 },
  next_lesson: {
    track_id: "track-1",
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
    vi.spyOn(gamificationService, "fetchRanking").mockResolvedValue({
      top: [{ user_id: "1", name: "Eu", score: 720, position: 12 }],
      current_user: { user_id: "1", name: "Eu", score: 720, position: 12 },
      total_users: 340,
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("120")).toBeInTheDocument()
    })

    expect(screen.getByText(/nível 3/i)).toBeInTheDocument()
    expect(screen.getByText(/faltam 80 xp/i)).toBeInTheDocument()

    expect(screen.getByText("5")).toBeInTheDocument()
    expect(screen.getByText(/dias consecutivos/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText("#12")).toBeInTheDocument()
    })
    expect(screen.getByText(/de 340 usuários/i)).toBeInTheDocument()

    expect(screen.getByText("Claude Chat")).toBeInTheDocument()
    expect(screen.getByText("Prompts eficazes")).toBeInTheDocument()
  })

  it("mostra estado de streak zerado com mensagem de incentivo", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(emptyDashboard)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/comece hoje/i)).toBeInTheDocument()
    })
  })

  it("mostra estado vazio de ranking quando não há usuário no ranking", async () => {
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

  it("mostra link real para começar a próxima missão", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(fullDashboard)

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /começar/i })).toBeInTheDocument()
    })

    expect(screen.getByRole("link", { name: /começar/i })).toHaveAttribute(
      "href",
      "/tracks/track-1/lessons/lesson-1"
    )
  })

  it("mostra estado de em breve honesto para badges e certificados quando o usuário não tem nenhum", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(fullDashboard)

    renderPage()

    await waitFor(() => {
      expect(
        screen.getByText(/em breve você poderá conquistar badges por aqui/i)
      ).toBeInTheDocument()
    })

    expect(
      screen.getByText(/conclua todas as missões de uma trilha para liberar o certificado/i)
    ).toBeInTheDocument()
  })

  it("mostra badges e certificados reais quando o usuário já os conquistou", async () => {
    vi.spyOn(dashboardService, "fetchDashboard").mockResolvedValue(fullDashboard)
    vi.spyOn(gamificationService, "fetchMyBadges").mockResolvedValue([
      {
        id: "ub1",
        badge_id: "b1",
        earned_at: "2026-07-06T00:00:00Z",
        badge: {
          id: "b1",
          name: "Primeiro Login",
          description: "Concedido ao acessar a plataforma pela primeira vez.",
          image: null,
          category: "bronze",
        },
      },
    ])
    vi.spyOn(gamificationService, "fetchMyCertificates").mockResolvedValue([
      {
        id: "uc1",
        certificate_id: "c1",
        title: "Certificado Claude Chat",
        hours: 4,
        validation_code: "codigo-123",
        issued_at: "2026-07-06T00:00:00Z",
        pdf_url: null,
      },
    ])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Primeiro Login")).toBeInTheDocument()
    })
    expect(screen.getByText("Certificado Claude Chat")).toBeInTheDocument()
    expect(screen.getByText(/4h · codigo-123/)).toBeInTheDocument()
  })
})
