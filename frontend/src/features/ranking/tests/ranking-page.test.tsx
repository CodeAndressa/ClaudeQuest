import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

import * as gamificationService from "@/features/dashboard/services/gamification-service"
import { RankingPage } from "@/features/ranking/pages/ranking-page"
import i18n from "@/i18n"
import { useAuthStore } from "@/store/auth-store"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

describe("RankingPage", () => {
  it("exibe o Top 10 e destaca a pessoa autenticada", async () => {
    useAuthStore.setState({
      user: { id: "user-1", name: "Ana", email: "ana@example.com", role: "student" },
    })
    vi.spyOn(gamificationService, "fetchRanking").mockResolvedValue({
      top: [
        { user_id: "user-1", name: "Ana", score: 850, position: 1 },
        { user_id: "user-2", name: "Bruno", score: 610, position: 2 },
      ],
      current_user: { user_id: "user-1", name: "Ana", score: 850, position: 1 },
      total_users: 2,
    })
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <I18nextProvider i18n={i18n}>
          <RankingPage />
        </I18nextProvider>
      </QueryClientProvider>
    )

    expect(await screen.findByRole("heading", { name: /quem está avançando/i })).toBeInTheDocument()
    expect(await screen.findByText("Ana")).toBeInTheDocument()
    expect(screen.getByText("Bruno")).toBeInTheDocument()
    expect(screen.getByText("Você")).toBeInTheDocument()
    expect(screen.getAllByText("850").length).toBeGreaterThan(0)
  })
})
