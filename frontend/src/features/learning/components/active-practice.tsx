import { useEffect, useState } from "react"
import { Check, ClipboardCheck, Lightbulb, PenLine } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { LessonDetail } from "@/features/learning/types/learning"
import { cn } from "@/lib/utils"

export function ActivePractice({
  lesson,
  onReadyChange,
}: {
  lesson: LessonDetail
  onReadyChange: (ready: boolean) => void
}) {
  const { t } = useTranslation()
  const [checked, setChecked] = useState<string[]>([])
  const [reflection, setReflection] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const isChecklist = lesson.lesson_type === "checklist"
  const ready = isChecklist
    ? lesson.questions.length > 0 && checked.length === lesson.questions.length
    : submitted && reflection.trim().length >= 80

  useEffect(() => onReadyChange(ready), [onReadyChange, ready])

  if (isChecklist) {
    return (
      <Card className="practice-enter overflow-hidden border-0 bg-transparent">
        <CardHeader className="border-b border-border">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <ClipboardCheck className="size-5" aria-hidden="true" />
            </span>
            <div>
              <h2 className="font-semibold text-foreground">{t("lesson.checklist.title")}</h2>
              <p className="text-sm text-muted-foreground">{t("lesson.checklist.description")}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 pt-5">
          {lesson.questions.map((question, index) => {
            const selected = checked.includes(question.id)
            return (
              <button
                key={question.id}
                type="button"
                aria-pressed={selected}
                onClick={() =>
                  setChecked((current) =>
                    selected
                      ? current.filter((id) => id !== question.id)
                      : [...current, question.id]
                  )
                }
                className={cn(
                  "practice-item flex min-h-14 items-start gap-3 rounded-lg border px-4 py-3 text-left transition-[border-color,background-color,transform] duration-200",
                  selected
                    ? "border-primary/60 bg-primary/10"
                    : "border-border bg-background hover:border-primary/40"
                )}
                style={{ animationDelay: `${Math.min(index, 6) * 45}ms` }}
              >
                <span
                  className={cn(
                    "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md border transition-colors",
                    selected ? "border-primary bg-primary text-primary-foreground" : "border-border"
                  )}
                >
                  {selected ? <Check className="size-4" aria-hidden="true" /> : null}
                </span>
                <span className="text-sm leading-6 text-foreground">{question.question}</span>
              </button>
            )
          })}
          <p className="mt-2 text-sm text-muted-foreground" role="status">
            {t("lesson.checklist.progress", {
              completed: checked.length,
              total: lesson.questions.length,
            })}
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="practice-enter overflow-hidden border-0 bg-transparent">
      <CardHeader className="border-b border-border">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <PenLine className="size-5" aria-hidden="true" />
          </span>
          <div>
            <h2 className="font-semibold text-foreground">{t("lesson.reflection.title")}</h2>
            <p className="text-sm text-muted-foreground">{t("lesson.reflection.description")}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 pt-5">
        <label htmlFor="lesson-reflection" className="text-base font-medium text-foreground">
          {lesson.questions[0]?.question ?? lesson.description}
        </label>
        <textarea
          id="lesson-reflection"
          value={reflection}
          disabled={submitted}
          onChange={(event) => setReflection(event.target.value)}
          placeholder={t("lesson.reflection.placeholder")}
          className="min-h-36 resize-y rounded-lg border border-input bg-background px-4 py-3 text-sm leading-6 text-foreground outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-80"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-muted-foreground">
            {t("lesson.reflection.characters", { count: reflection.trim().length })}
          </span>
          <Button
            type="button"
            disabled={reflection.trim().length < 80 || submitted}
            onClick={() => setSubmitted(true)}
          >
            {submitted ? t("lesson.reflection.submitted") : t("lesson.reflection.review")}
          </Button>
        </div>
        {submitted ? (
          <div className="feedback-reveal flex gap-3 rounded-lg border border-primary/40 bg-primary/10 p-4">
            <Lightbulb className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
            <div>
              <p className="font-medium text-foreground">{t("lesson.reflection.reference")}</p>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {lesson.questions[0]?.explanation ?? lesson.description}
              </p>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
