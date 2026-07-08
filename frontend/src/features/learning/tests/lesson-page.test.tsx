import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { LessonPage } from "@/features/learning/pages/lesson-page"
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
        <MemoryRouter initialEntries={["/tracks/track-1/lessons/lesson-1"]}>
          <Routes>
            <Route path="/tracks/:trackId/lessons/:lessonId" element={<LessonPage />} />
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
  total_lessons: 1,
  completed_lessons: 1,
  progress_percent: 100,
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
          estimated_minutes: 10,
          xp: 50,
          stars: 1,
          required_xp: 0,
          lessons: [
            {
              id: "lesson-1",
              title: "Primeira missão",
              description: "Aprenda o básico.",
              content: "## Um começo\n\nConteúdo da missão.",
              estimated_minutes: 10,
              difficulty: "beginner",
              lesson_type: "reading",
              order: 1,
              xp: 50,
              ai_corrected: false,
              completed: true,
              questions: [],
            },
          ],
        },
      ],
    },
  ],
}

const trackDetailWithQuestion: TrackDetail = {
  ...trackDetail,
  modules: [
    {
      ...trackDetail.modules[0],
      levels: [
        {
          ...trackDetail.modules[0].levels[0],
          lessons: [
            {
              id: "lesson-1",
              title: "Primeira missão",
              description: "Aprenda o básico.",
              content: "## Um começo\n\nConteúdo da missão.",
              estimated_minutes: 10,
              difficulty: "beginner",
              lesson_type: "quiz",
              order: 1,
              xp: 50,
              ai_corrected: false,
              completed: false,
              questions: [
                {
                  id: "question-1",
                  question: "Qual comando inicia o backend?",
                  question_type: "single_choice",
                  explanation: "O backend roda com uvicorn na porta 8002.",
                  points: 10,
                  order: 1,
                  alternatives: [
                    {
                      id: "alt-correct",
                      text: "uv run uvicorn app.main:app --reload --port 8002",
                      is_correct: true,
                      feedback: "Isso mesmo! Esse é o comando usado no projeto.",
                      order: 1,
                    },
                    {
                      id: "alt-wrong",
                      text: "npm run dev",
                      is_correct: false,
                      feedback: "Esse comando sobe o frontend, não o backend.",
                      order: 2,
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
  ],
}

describe("LessonPage", () => {
  it("mostra estado de missão concluída e desabilita nova conclusão", async () => {
    const completeSpy = vi.spyOn(learningService, "completeLesson")
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetail)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Primeira missão")).toBeInTheDocument()
    })

    expect(screen.getByText("Concluída")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /missão concluída/i })).toBeDisabled()
    expect(completeSpy).not.toHaveBeenCalled()
  })

  it("não revela a resposta correta nem feedback antes de qualquer seleção", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetailWithQuestion)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Qual comando inicia o backend?")).toBeInTheDocument()
    })

    expect(screen.queryByText("Isso mesmo! Esse é o comando usado no projeto.")).not.toBeInTheDocument()
    expect(screen.queryByText("Esse comando sobe o frontend, não o backend.")).not.toBeInTheDocument()
    expect(screen.queryByText("O backend roda com uvicorn na porta 8002.")).not.toBeInTheDocument()

    const options = screen.getAllByRole("radio")
    for (const option of options) {
      expect(option).toHaveAttribute("aria-checked", "false")
    }

    expect(screen.queryByRole("button", { name: "Verificar resposta" })).not.toBeInTheDocument()
  })

  it("revela o feedback automaticamente ao selecionar a alternativa correta", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetailWithQuestion)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Qual comando inicia o backend?")).toBeInTheDocument()
    })

    const correctOption = screen.getByRole("radio", {
      name: /uv run uvicorn app\.main:app --reload --port 8002/,
    })
    await userEvent.click(correctOption)
    expect(correctOption).toHaveAttribute("aria-checked", "true")

    expect(screen.getByText("Isso mesmo! Esse é o comando usado no projeto.")).toBeInTheDocument()
    expect(screen.getByText("O backend roda com uvicorn na porta 8002.")).toBeInTheDocument()
    expect(correctOption).toBeDisabled()
  })

  it("destaca a alternativa correta quando o aluno seleciona a errada", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetailWithQuestion)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Qual comando inicia o backend?")).toBeInTheDocument()
    })

    const wrongOption = screen.getByRole("radio", { name: /npm run dev/ })
    await userEvent.click(wrongOption)

    const correctOption = screen.getByRole("radio", {
      name: /uv run uvicorn app\.main:app --reload --port 8002/,
    })

    expect(screen.getByText("Esse comando sobe o frontend, não o backend.")).toBeInTheDocument()
    expect(screen.getByText("Isso mesmo! Esse é o comando usado no projeto.")).toBeInTheDocument()
    expect(correctOption).toHaveClass("border-emerald-400")
    expect(wrongOption).toHaveClass("border-red-400")
  })

  it("mostra o estado de erro e permite tentar novamente quando o backend falha", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockRejectedValue(new Error("network down"))

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument()
    })

    const fetchSpy = vi.spyOn(learningService, "fetchTrackDetail")
    await userEvent.click(screen.getByRole("button", { name: /tentar novamente/i }))

    expect(fetchSpy).toHaveBeenCalled()
  })

  it("mostra estado de erro quando a missão não é encontrada na trilha", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetail)

    render(
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <MemoryRouter initialEntries={["/tracks/track-1/lessons/lesson-inexistente"]}>
            <Routes>
              <Route path="/tracks/:trackId/lessons/:lessonId" element={<LessonPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </I18nextProvider>
    )

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument()
    })

    const alert = screen.getByRole("alert")
    expect(within(alert).getByRole("link", { name: /voltar para a trilha/i })).toHaveAttribute(
      "href",
      "/tracks/track-1"
    )
  })

  it("conclui a missão com sucesso e mostra o XP ganho", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetailWithQuestion)
    vi.spyOn(learningService, "completeLesson").mockResolvedValue({
      lesson_id: "lesson-1",
      completed: true,
      already_completed: false,
      xp_granted: 50,
      total_xp: 150,
      level: 2,
      xp_to_next_level: 50,
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Primeira missão")).toBeInTheDocument()
    })

    await userEvent.click(
      screen.getByRole("radio", { name: /uv run uvicorn app\.main:app --reload --port 8002/ })
    )

    const completeButton = screen.getByRole("button", { name: /concluir missão/i })
    expect(completeButton).toBeEnabled()
    await userEvent.click(completeButton)

    await waitFor(() => {
      expect(screen.getByRole("status")).toBeInTheDocument()
    })

    expect(screen.getByText("Missão concluída. Você ganhou 50 XP.")).toBeInTheDocument()
  })

  it("mantém o botão de concluir desabilitado enquanto o quiz não for respondido corretamente", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetailWithQuestion)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Primeira missão")).toBeInTheDocument()
    })

    expect(screen.getByRole("button", { name: /concluir missão/i })).toBeDisabled()
    expect(screen.getByText(/responda corretamente todas as questões/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole("radio", { name: /npm run dev/ }))

    expect(screen.getByRole("button", { name: /concluir missão/i })).toBeDisabled()

    await userEvent.click(screen.getByRole("button", { name: /tentar de novo/i }))
    await userEvent.click(
      screen.getByRole("radio", { name: /uv run uvicorn app\.main:app --reload --port 8002/ })
    )

    expect(screen.getByRole("button", { name: /concluir missão/i })).toBeEnabled()
  })

  it("mostra mensagem de erro quando a conclusão da missão falha", async () => {
    vi.spyOn(learningService, "fetchTrackDetail").mockResolvedValue(trackDetailWithQuestion)
    vi.spyOn(learningService, "completeLesson").mockRejectedValue(new Error("falhou"))

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Primeira missão")).toBeInTheDocument()
    })

    await userEvent.click(
      screen.getByRole("radio", { name: /uv run uvicorn app\.main:app --reload --port 8002/ })
    )
    await userEvent.click(screen.getByRole("button", { name: /concluir missão/i }))

    await waitFor(() => {
      expect(screen.getByText(/não foi possível concluir esta missão agora/i)).toBeInTheDocument()
    })
  })
})
