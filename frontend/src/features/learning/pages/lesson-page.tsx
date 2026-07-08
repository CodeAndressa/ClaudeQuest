import { useEffect, useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "react-router"
import { useTranslation } from "react-i18next"
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Loader2,
  RotateCcw,
  Sparkles,
  XCircle,
} from "lucide-react"

import { completeLesson, fetchTrackDetail } from "@/features/learning/services/learning-service"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { LessonDetail } from "@/features/learning/types/learning"

function LessonSkeleton() {
  return (
    <div role="status" aria-busy="true" className="flex flex-col gap-4">
      <Skeleton className="h-8 w-2/3" />
      <Skeleton className="h-4 w-1/2" />
      <Card>
        <CardContent className="flex flex-col gap-3 pt-6">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    </div>
  )
}

function findLesson(
  track: Awaited<ReturnType<typeof fetchTrackDetail>> | undefined,
  lessonId: string | undefined
) {
  if (!track || !lessonId) return null

  for (const module of track.modules) {
    for (const level of module.levels) {
      const lesson = level.lessons.find((candidate) => candidate.id === lessonId)
      if (lesson) return lesson
    }
  }

  return null
}

function LessonContent({ content }: { content: string }) {
  const blocks = content.split("\n\n").filter(Boolean)

  return (
    <div className="flex flex-col gap-4 text-sm leading-7 text-foreground">
      {blocks.map((block, index) => {
        if (block.startsWith("# ")) return null

        if (block.startsWith("## ")) {
          return (
            <h2 key={index} className="pt-2 text-lg font-semibold leading-tight text-foreground">
              {block.replace("## ", "")}
            </h2>
          )
        }

        return (
          <p key={index} className="whitespace-pre-line text-muted-foreground">
            {block}
          </p>
        )
      })}
    </div>
  )
}

function isQuestionCorrect(
  question: LessonDetail["questions"][number],
  selectedId: string | undefined
): boolean {
  if (!selectedId) return false
  const selected = question.alternatives.find((alternative) => alternative.id === selectedId)
  return Boolean(selected?.is_correct)
}

function Questions({
  lesson,
  onAllCorrectChange,
}: {
  lesson: LessonDetail
  onAllCorrectChange: (allCorrect: boolean) => void
}) {
  const { t } = useTranslation()
  const [selectedByQuestion, setSelectedByQuestion] = useState<Record<string, string>>({})
  const [verifiedQuestions, setVerifiedQuestions] = useState<Record<string, boolean>>({})
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)

  const allCorrect =
    lesson.questions.length > 0 &&
    lesson.questions.every(
      (question) =>
        verifiedQuestions[question.id] &&
        isQuestionCorrect(question, selectedByQuestion[question.id])
    )

  useEffect(() => {
    onAllCorrectChange(allCorrect)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allCorrect])

  if (lesson.questions.length === 0) return null

  const safeQuestionIndex = Math.min(currentQuestionIndex, lesson.questions.length - 1)
  const currentQuestion = lesson.questions[safeQuestionIndex]
  const alternatives = [...currentQuestion.alternatives].sort((a, b) => a.order - b.order)
  const selectedId = selectedByQuestion[currentQuestion.id] ?? null
  const isVerified = verifiedQuestions[currentQuestion.id] ?? false
  const currentCorrect = isQuestionCorrect(currentQuestion, selectedId ?? undefined)
  const canGoNext = isVerified && currentCorrect && safeQuestionIndex < lesson.questions.length - 1
  const answeredCount = lesson.questions.filter(
    (question) =>
      verifiedQuestions[question.id] && isQuestionCorrect(question, selectedByQuestion[question.id])
  ).length
  const progressPercent = Math.round((answeredCount / lesson.questions.length) * 100)

  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-foreground">{t("lesson.practiceTitle")}</h2>
          <span className="text-sm font-medium text-muted-foreground">
            {t("lesson.questionProgress", {
              current: safeQuestionIndex + 1,
              total: lesson.questions.length,
            })}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="flex flex-col gap-3">
          <p className="text-base font-medium text-foreground">{currentQuestion.question}</p>
          <div className="grid gap-2" role="radiogroup" aria-label={currentQuestion.question}>
            {alternatives.map((alternative) => {
              const isSelected = alternative.id === selectedId
              const isCorrectHighlight = isVerified && alternative.is_correct
              const isWrongSelected = isVerified && isSelected && !alternative.is_correct
              const showFeedback = isVerified && (isSelected || alternative.is_correct)

              return (
                <button
                  key={alternative.id}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  disabled={isVerified}
                  onClick={() => {
                    setSelectedByQuestion((prev) => ({
                      ...prev,
                      [currentQuestion.id]: alternative.id,
                    }))
                    setVerifiedQuestions((prev) => ({ ...prev, [currentQuestion.id]: true }))
                  }}
                  className={cn(
                    "flex min-h-12 w-full items-start gap-3 rounded-md border px-3 py-3 text-left text-sm transition-colors",
                    "disabled:cursor-not-allowed",
                    isCorrectHighlight
                      ? "border-emerald-400 bg-emerald-400/10"
                      : isWrongSelected
                        ? "border-red-400 bg-red-400/10"
                        : isSelected
                          ? "border-primary bg-primary/10"
                          : "border-border bg-background"
                  )}
                >
                  {isVerified ? (
                    alternative.is_correct ? (
                      <CheckCircle2
                        className="mt-0.5 size-4 shrink-0 text-emerald-400"
                        aria-hidden="true"
                      />
                    ) : isSelected ? (
                      <XCircle className="mt-0.5 size-4 shrink-0 text-red-400" aria-hidden="true" />
                    ) : (
                      <span
                        className="mt-1.5 size-2 shrink-0 rounded-full bg-muted-foreground/60"
                        aria-hidden="true"
                      />
                    )
                  ) : (
                    <span
                      className={cn(
                        "mt-1.5 size-2 shrink-0 rounded-full",
                        isSelected ? "bg-primary" : "bg-muted-foreground/60"
                      )}
                      aria-hidden="true"
                    />
                  )}
                  <div className="flex flex-col gap-1">
                    <span className="text-foreground">{alternative.text}</span>
                    {showFeedback && alternative.feedback ? (
                      <span className="text-xs text-muted-foreground">{alternative.feedback}</span>
                    ) : null}
                  </div>
                </button>
              )
            })}
          </div>
          {!isVerified ? (
            <p className="text-xs text-muted-foreground">{t("lesson.selectHint")}</p>
          ) : null}
          {isVerified && currentQuestion.explanation ? (
            <p className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
              {currentQuestion.explanation}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isVerified && !currentCorrect ? (
            <Button
              type="button"
              variant="ghost"
              className="w-fit"
              onClick={() => {
                setSelectedByQuestion((prev) => {
                  const next = { ...prev }
                  delete next[currentQuestion.id]
                  return next
                })
                setVerifiedQuestions((prev) => {
                  const next = { ...prev }
                  delete next[currentQuestion.id]
                  return next
                })
              }}
            >
              <RotateCcw className="size-4" aria-hidden="true" />
              {t("lesson.tryAgain")}
            </Button>
          ) : null}
          {canGoNext ? (
            <Button
              type="button"
              className="w-fit"
              onClick={() => setCurrentQuestionIndex((index) => index + 1)}
            >
              {t("lesson.continue")}
            </Button>
          ) : null}
          {allCorrect ? (
            <span className="text-sm font-medium text-emerald-400">{t("lesson.practiceDone")}</span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

export function LessonPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { trackId, lessonId } = useParams<{ trackId: string; lessonId: string }>()
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["learning", "tracks", trackId],
    queryFn: () => fetchTrackDetail(trackId!),
    enabled: Boolean(trackId),
  })
  const completeMutation = useMutation({
    mutationFn: () => completeLesson(lessonId!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["learning", "tracks"] })
      void queryClient.invalidateQueries({ queryKey: ["learning", "tracks", trackId] })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      void queryClient.invalidateQueries({ queryKey: ["gamification"] })
    },
  })

  const lesson = useMemo(() => findLesson(data, lessonId), [data, lessonId])
  const [quizAllCorrect, setQuizAllCorrect] = useState(false)
  const hasQuestions = (lesson?.questions.length ?? 0) > 0
  const canComplete = !hasQuestions || quizAllCorrect

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-8">
      <Link
        to={trackId ? `/tracks/${trackId}` : "/tracks"}
        className="flex w-fit items-center gap-2 text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        {t("lesson.back")}
      </Link>

      {isLoading && <LessonSkeleton />}

      {isError && (
        <div className="flex flex-col items-center gap-3 py-12" role="alert">
          <p className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="size-4" aria-hidden="true" />
            {t("lesson.error")}
          </p>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
            {t("lesson.retry")}
          </Button>
        </div>
      )}

      {data && !lesson && (
        <div className="flex flex-col items-center gap-3 py-12" role="alert">
          <p className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="size-4" aria-hidden="true" />
            {t("lesson.error")}
          </p>
          <Button asChild variant="outline">
            <Link to={`/tracks/${data.id}`}>{t("lesson.back")}</Link>
          </Button>
        </div>
      )}

      {lesson && (
        <>
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Sparkles className="size-4 text-primary" aria-hidden="true" />
                {t(`lesson.type.${lesson.lesson_type}`, { defaultValue: lesson.lesson_type })}
              </span>
              <span className="inline-flex items-center gap-1">
                <Clock className="size-4" aria-hidden="true" />
                {t("lesson.estimatedMinutes", { count: lesson.estimated_minutes })}
              </span>
              <span>{t("lesson.xp", { count: lesson.xp })}</span>
              {lesson.completed ? (
                <span className="inline-flex items-center gap-1 font-medium text-emerald-400">
                  <CheckCircle2 className="size-4" aria-hidden="true" />
                  {t("lesson.completedBadge")}
                </span>
              ) : null}
            </div>
            <h1 className="text-2xl font-semibold text-foreground">{lesson.title}</h1>
            <p className="text-sm text-muted-foreground">{lesson.description}</p>
          </div>

          <Card>
            <CardContent className="pt-6">
              <LessonContent content={lesson.content} />
            </CardContent>
          </Card>

          <Questions key={lesson.id} lesson={lesson} onAllCorrectChange={setQuizAllCorrect} />

          <div className="flex flex-col gap-3">
            <Button
              type="button"
              className="w-full md:w-fit"
              variant={lesson.completed ? "outline" : "default"}
              disabled={completeMutation.isPending || lesson.completed || !lessonId || !canComplete}
              onClick={() => completeMutation.mutate()}
            >
              {completeMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              ) : null}
              {lesson.completed ? t("lesson.completedCta") : t("lesson.completeCta")}
            </Button>
            {!lesson.completed && !canComplete ? (
              <p className="text-sm text-muted-foreground">{t("lesson.answerToComplete")}</p>
            ) : null}
            {completeMutation.isSuccess ? (
              <p role="status" className="text-sm text-emerald-400">
                {completeMutation.data.already_completed
                  ? t("lesson.alreadyCompleted")
                  : t("lesson.completed", { xp: completeMutation.data.xp_granted })}
              </p>
            ) : null}
            {completeMutation.isError ? (
              <p role="alert" className="text-sm text-destructive">
                {t("lesson.completeError")}
              </p>
            ) : null}
          </div>
        </>
      )}
    </div>
  )
}
