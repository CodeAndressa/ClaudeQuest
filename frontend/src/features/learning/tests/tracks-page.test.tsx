import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter } from "react-router"
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { TracksPage } from "@/features/learning/pages/tracks-page"
import * as learningService from "@/features/learning/services/learning-service"
import type { TrackSummary } from "@/features/learning/types/learning"

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
        <MemoryRouter>
          <TracksPage />
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  )
}

const tracks: TrackSummary[] = [
  {
    id: "track-2",
    title: "Claude Avançado",
    description: "Técnicas avançadas de prompting.",
    difficulty: "advanced",
    estimated_hours: 6,
    total_lessons: 4,
    completed_lessons: 2,
    progress_percent: 50,
    image: null,
    icon: null,
    order: 2,
  },
  {
    id: "track-1",
    title: "Claude Chat",
    description: "Introdução ao Claude.",
    difficulty: "beginner",
    estimated_hours: 3,
    total_lessons: 2,
    completed_lessons: 0,
    progress_percent: 0,
    image: null,
    icon: null,
    order: 1,
  },
]

describe("TracksPage", () => {
  it("mostra o skeleton de carregamento antes da resposta chegar", () => {
    vi.spyOn(learningService, "fetchTracks").mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByRole("status", { name: "" })).toBeInTheDocument()
  })

  it("mostra o estado de erro e permite tentar novamente quando o backend falha", async () => {
    vi.spyOn(learningService, "fetchTracks").mockRejectedValue(new Error("network down"))

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument()
    })

    const fetchSpy = vi.spyOn(learningService, "fetchTracks")
    await userEvent.click(screen.getByRole("button", { name: /tentar novamente/i }))

    expect(fetchSpy).toHaveBeenCalled()
  })

  it("mostra a mensagem de estado vazio quando não há trilhas", async () => {
    vi.spyOn(learningService, "fetchTracks").mockResolvedValue([])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/nenhuma trilha disponível no momento/i)).toBeInTheDocument()
    })
  })

  it("mostra as trilhas ordenadas com título, dificuldade, horas, progresso e link para a trilha", async () => {
    vi.spyOn(learningService, "fetchTracks").mockResolvedValue(tracks)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("Claude Chat")).toBeInTheDocument()
    })

    expect(screen.getByText("Claude Avançado")).toBeInTheDocument()
    expect(screen.getByText("Iniciante")).toBeInTheDocument()
    expect(screen.getByText("Avançado")).toBeInTheDocument()
    expect(screen.getByText("3h")).toBeInTheDocument()
    expect(screen.getByText("6h")).toBeInTheDocument()
    expect(screen.getByText("0 de 2 missões concluídas")).toBeInTheDocument()
    expect(screen.getByText("2 de 4 missões concluídas")).toBeInTheDocument()
    expect(screen.getByRole("progressbar", { name: "2 de 4 missões concluídas" })).toHaveAttribute(
      "aria-valuenow",
      "50"
    )

    const links = screen.getAllByRole("link", { name: /ver trilha/i })
    expect(links).toHaveLength(2)
    expect(links[0]).toHaveAttribute("href", "/tracks/track-1")
    expect(links[1]).toHaveAttribute("href", "/tracks/track-2")
  })
})
