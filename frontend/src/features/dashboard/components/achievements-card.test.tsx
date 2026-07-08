import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { AchievementsCard } from "@/features/dashboard/components/achievements-card"
import * as gamificationService from "@/features/dashboard/services/gamification-service"
import type { UserAchievement } from "@/features/dashboard/types/gamification"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <AchievementsCard />
      </QueryClientProvider>
    </I18nextProvider>
  )
}

describe("AchievementsCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it("mostra o estado de carregamento antes da resposta chegar", () => {
    vi.spyOn(gamificationService, "fetchMyAchievements").mockReturnValue(new Promise(() => {}))

    renderCard()

    expect(screen.getByRole("status")).toBeInTheDocument()
  })

  it("mostra mensagem de estado vazio quando o usuário não tem achievements", async () => {
    vi.spyOn(gamificationService, "fetchMyAchievements").mockResolvedValue([])

    renderCard()

    await waitFor(() => {
      expect(screen.queryByRole("status")).not.toBeInTheDocument()
    })
  })

  it("mostra os achievements conquistados pelo usuário", async () => {
    const achievements: UserAchievement[] = [
      {
        id: "ua1",
        achievement_id: "a1",
        achieved_at: "2026-07-06T00:00:00Z",
        achievement: {
          id: "a1",
          name: "Primeira Missão",
          description: "Concluiu a primeira lição.",
          icon: "footprints",
          metric: "lessons_completed",
          threshold: 1,
        },
      },
    ]
    vi.spyOn(gamificationService, "fetchMyAchievements").mockResolvedValue(achievements)

    renderCard()

    await waitFor(() => {
      expect(screen.getByText("Primeira Missão")).toBeInTheDocument()
    })
  })
})
