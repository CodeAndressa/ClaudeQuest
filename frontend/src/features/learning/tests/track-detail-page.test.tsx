import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { TrackDetailPage } from "@/features/learning/pages/track-detail-page"
import * as learningService from "@/features/learning/services/learning-service"
import type { TrackDetail } from "@/features/learning/types/learning"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

afterEach(() => {
  vi.restoreAllMocks()
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/tracks/track-1"]}>
          <Routes>
            <Route path="/tracks/:trackId" element={<TrackDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  )
}

const trackDetail: TrackDetail = {
  id: "track-1",
  title: "Claude Chat",
  description: "Introdução ao Claude.",
  difficulty: "beginner",
  estimated_hours: 3,
  total_lessons: 2,
  completed_lessons: 1,
  progress_percent: 50,
  image: null,
  icon: null,
  order: 1,
  is_active: true,
  modules: [
    {
      id: "module-1",
      title: "Fundamentos",
      description: "Primeiros passos.",
      order: 1,
      levels: [
        {
          id: "level-1",
          title: "Começo",
          description: "Base.",
          level_number: 1,
          estimated_minutes: 20,
          xp: 100,
          stars: 1,
          required_xp: 0,
          lessons: [
            {
              id: "lesson-1",
              title: "Primeira missão",
              description: "Aprenda o básico.",
              content: "Conteúdo",
              estimated_minutes: 10,
              difficulty: "beginner",
              lesson_type: "reading",
              order: 1,
              xp: 50,
              ai_corrected: false,
              completed: true,
              questions: [],
            },
            {
              id: "lesson-2",
              title: "Segunda missão",
              description: "Continue praticando.",
              content: "Conteúdo",
              estimated_minutes: 10,
              difficulty: "beginner",
              lesson_type: "quiz",
              order: 2,
              xp: 50,
              ai_corrected: false,
              completed: false,
              questions: [],
            },
          ],
        },
      ],
    },
  ],
}

describe("TrackDetailPage", () => {
  it("mostra progresso real da trilha e destaca missões concluídas", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetail)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Claude Chat")).toBeInTheDocument()
    })

    expect(screen.getByText("1 de 2 missões concluídas")).toBeInTheDocument()
    expect(screen.getByRole("progressbar", { name: "1 de 2 missões concluídas" })).toHaveAttribute(
      "aria-valuenow",
      "50"
    )
    expect(screen.getByText("Primeira missão")).toBeInTheDocument()
    expect(screen.getByText("Segunda missão")).toBeInTheDocument()
    expect(screen.getByText("Concluída")).toBeInTheDocument()
  })
})
