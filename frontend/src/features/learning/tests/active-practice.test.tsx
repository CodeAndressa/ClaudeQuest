import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

import { ActivePractice } from "@/features/learning/components/active-practice"
import type { LessonDetail } from "@/features/learning/types/learning"
import i18n from "@/i18n"

const baseLesson: LessonDetail = {
  id: "lesson-1",
  title: "Decisão responsável",
  description: "Aplique o conceito.",
  content: "Conteúdo",
  estimated_minutes: 8,
  difficulty: "beginner",
  lesson_type: "checklist",
  order: 1,
  xp: 35,
  ai_corrected: false,
  completed: false,
  questions: [
    {
      id: "question-1",
      question: "Verifiquei as evidências antes de decidir?",
      question_type: "multiple_choice",
      explanation: "Use evidências confiáveis.",
      points: 1,
      order: 1,
      alternatives: [],
    },
  ],
}

beforeAll(async () => i18n.changeLanguage("pt-BR"))

describe("ActivePractice", () => {
  it("conclui um checklist de domínio", async () => {
    const onReadyChange = vi.fn()
    render(
      <I18nextProvider i18n={i18n}>
        <ActivePractice lesson={baseLesson} onReadyChange={onReadyChange} />
      </I18nextProvider>
    )

    await userEvent.click(screen.getByRole("button", { name: /verifiquei as evidências/i }))
    expect(onReadyChange).toHaveBeenLastCalledWith(true)
  })

  it("exige uma reflexão significativa antes da comparação", async () => {
    const lesson: LessonDetail = { ...baseLesson, lesson_type: "free_answer" }
    render(
      <I18nextProvider i18n={i18n}>
        <ActivePractice lesson={lesson} onReadyChange={vi.fn()} />
      </I18nextProvider>
    )

    const textarea = screen.getByLabelText(/verifiquei as evidências/i)
    await userEvent.type(
      textarea,
      "Eu verificaria a fonte, compararia os dados disponíveis e registraria os riscos antes de tomar a decisão final."
    )
    await userEvent.click(screen.getByRole("button", { name: /comparar raciocínio/i }))
    expect(screen.getByText(/ponto de referência/i)).toBeInTheDocument()
  })
})
