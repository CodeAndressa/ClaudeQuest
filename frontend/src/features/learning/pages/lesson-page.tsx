import { useEffect, useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "react-router"
import { useTranslation } from "react-i18next"
import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  CheckCircle2,
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
import { ActivePractice } from "@/features/learning/components/active-practice"
import { LessonJourney } from "@/features/learning/components/lesson-journey"

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
  selectedId: string | undefined,
  orderedIds: string[] | undefined
): boolean {
  if (question.question_type === "drag_and_drop") {
    const expected = [...question.alternatives]
      .sort((a, b) => a.order - b.order)
      .map((alternative) => alternative.id)
    return Boolean(orderedIds && expected.every((id, index) => orderedIds[index] === id))
  }
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
  const [orderedByQuestion, setOrderedByQuestion] = useState<Record<string, string[]>>({})
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [confidence, setConfidence] = useState(3)

  const allCorrect =
    lesson.questions.length > 0 &&
    lesson.questions.every(
      (question) =>
        verifiedQuestions[question.id] &&
        isQuestionCorrect(question, selectedByQuestion[question.id], orderedByQuestion[question.id])
    )

  useEffect(() => {
    onAllCorrectChange(allCorrect)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allCorrect])

  if (lesson.questions.length === 0) return null

  const safeQuestionIndex = Math.min(currentQuestionIndex, lesson.questions.length - 1)
  const currentQuestion = lesson.questions[safeQuestionIndex]
  const alternatives = [...currentQuestion.alternatives].sort((a, b) => a.order - b.order)
  const orderedIds =
    orderedByQuestion[currentQuestion.id] ??
    (currentQuestion.question_type === "drag_and_drop"
      ? [...alternatives].reverse().map((alternative) => alternative.id)
      : [])
  const selectedId = selectedByQuestion[currentQuestion.id] ?? null
  const isVerified = verifiedQuestions[currentQuestion.id] ?? false
  const currentCorrect = isQuestionCorrect(currentQuestion, selectedId ?? undefined, orderedIds)
  const canGoNext = isVerified && currentCorrect && safeQuestionIndex < lesson.questions.length - 1
  const answeredCount = lesson.questions.filter(
    (question) =>
      verifiedQuestions[question.id] &&
      isQuestionCorrect(question, selectedByQuestion[question.id], orderedByQuestion[question.id])
  ).length
  const progressPercent = Math.round((answeredCount / lesson.questions.length) * 100)

  return (
    <Card className="border-0 bg-transparent">
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
        <div key={currentQuestion.id} className="practice-enter flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
              {t(`lesson.cognitiveStep.${safeQuestionIndex % 4}`)}
            </span>
            {lesson.lesson_type === "challenge" ? (
              <span className="text-xs text-muted-foreground">
                {t("lesson.confidence.value", { value: confidence })}
              </span>
            ) : null}
          </div>
          <p className="text-base font-medium leading-7 text-foreground">
            {currentQuestion.question}
          </p>
          {currentQuestion.question_type === "drag_and_drop" ? (
            <div className="flex flex-col gap-2" aria-label={currentQuestion.question}>
              {orderedIds.map((alternativeId, index) => {
                const alternative = alternatives.find((item) => item.id === alternativeId)!
                return (
                  <div
                    key={alternative.id}
                    className={cn(
                      "flex min-h-14 items-center gap-3 rounded-md border px-3 py-2",
                      isVerified && currentCorrect
                        ? "border-emerald-400 bg-emerald-400/10"
                        : "border-border bg-background"
                    )}
                  >
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold text-foreground">
                      {index + 1}
                    </span>
                    <span className="flex-1 text-sm text-foreground">{alternative.text}</span>
                    <div className="flex gap-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        disabled={isVerified || index === 0}
                        aria-label={t("lesson.moveUp")}
                        onClick={() => {
                          const next = [...orderedIds]
                          ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                          setOrderedByQuestion((prev) => ({ ...prev, [currentQuestion.id]: next }))
                        }}
                      >
                        <ArrowUp className="size-4" aria-hidden="true" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        disabled={isVerified || index === orderedIds.length - 1}
                        aria-label={t("lesson.moveDown")}
                        onClick={() => {
                          const next = [...orderedIds]
                          ;[next[index + 1], next[index]] = [next[index], next[index + 1]]
                          setOrderedByQuestion((prev) => ({ ...prev, [currentQuestion.id]: next }))
                        }}
                      >
                        <ArrowDown className="size-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                )
              })}
              {!isVerified ? (
                <Button
                  type="button"
                  variant="outline"
                  className="mt-2 w-fit"
                  onClick={() => {
                    setOrderedByQuestion((prev) => ({
                      ...prev,
                      [currentQuestion.id]: orderedIds,
                    }))
                    setVerifiedQuestions((prev) => ({ ...prev, [currentQuestion.id]: true }))
                  }}
                >
                  {t("lesson.checkOrder")}
                </Button>
              ) : null}
            </div>
          ) : (
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
                        <XCircle
                          className="mt-0.5 size-4 shrink-0 text-red-400"
                          aria-hidden="true"
                        />
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
                        <span className="text-xs text-muted-foreground">
                          {alternative.feedback}
                        </span>
                      ) : null}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
          {lesson.lesson_type === "challenge" && !isVerified ? (
            <label className="mt-2 flex flex-col gap-2 text-sm text-muted-foreground">
              <span>{t("lesson.confidence.label")}</span>
              <input
                type="range"
                min="1"
                max="5"
                value={confidence}
                onChange={(event) => setConfidence(Number(event.target.value))}
                className="w-full accent-emerald-500"
              />
              <span className="flex justify-between text-xs">
                <span>{t("lesson.confidence.low")}</span>
                <span>{t("lesson.confidence.high")}</span>
              </span>
            </label>
          ) : null}
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
                if (currentQuestion.question_type === "drag_and_drop") {
                  setOrderedByQuestion((prev) => {
                    const next = { ...prev }
                    delete next[currentQuestion.id]
                    return next
                  })
                }
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
  const [activePracticeReady, setActivePracticeReady] = useState(false)
  const usesActivePractice =
    lesson?.lesson_type === "checklist" || lesson?.lesson_type === "free_answer"
  const hasQuestions = (lesson?.questions.length ?? 0) > 0
  const canComplete = usesActivePractice ? activePracticeReady : !hasQuestions || quizAllCorrect

  return (
    <div className="min-h-full bg-background">
      {isLoading ? (
        <div className="p-6 md:p-8">
          <LessonSkeleton />
        </div>
      ) : null}

      {isError && (
        <div className="flex flex-col items-center gap-3 p-12" role="alert">
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
        <div className="flex flex-col items-center gap-3 p-12" role="alert">
          <p className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="size-4" aria-hidden="true" />
            {t("lesson.error")}
          </p>
          <Button asChild variant="outline">
            <Link to={`/tracks/${data.id}`}>{t("lesson.back")}</Link>
          </Button>
        </div>
      )}

      {data && lesson ? (
        <>
          <header className="flex min-h-20 flex-wrap items-center gap-5 border-b border-border bg-[#050a08] px-5 py-4 md:px-7">
            <div className="min-w-0 flex-1">
              <Link
                to={`/tracks/${data.id}`}
                className="mb-1 flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="size-3" aria-hidden="true" />
                {t("lesson.back")}
              </Link>
              <p className="truncate font-medium text-foreground">{data.title}</p>
            </div>
            <div className="min-w-48 md:w-72">
              <div className="mb-2 flex justify-between text-xs text-muted-foreground">
                <span>{t("trackDetail.progressPercent", { percent: data.progress_percent })}</span>
                <span>
                  {data.completed_lessons} / {data.total_lessons}
                </span>
              </div>
              <div className="h-1 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-primary shadow-[0_0_12px_#34d399] transition-[width] duration-300"
                  style={{ width: `${data.progress_percent}%` }}
                />
              </div>
            </div>
          </header>

          <div className="grid lg:grid-cols-[320px_minmax(0,1fr)]">
            <LessonJourney track={data} currentLessonId={lesson.id} />
            <main className="min-w-0 p-5 md:p-7">
              <div className="mx-auto flex max-w-[1060px] flex-col gap-5">
                <div className="flex flex-col gap-3 border-b border-border pb-5">
                  <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <Sparkles className="size-4 text-primary" aria-hidden="true" />
                      {t(`lesson.type.${lesson.lesson_type}`, { defaultValue: lesson.lesson_type })}
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

                <div className="grid items-start overflow-hidden rounded-lg border border-border xl:grid-cols-[minmax(0,0.9fr)_minmax(500px,1.1fr)]">
                  <Card className="rounded-none border-0 border-b border-border bg-transparent xl:sticky xl:top-6 xl:border-b-0 xl:border-r">
                    <CardContent className="pt-6">
                      <LessonContent content={lesson.content} />
                    </CardContent>
                  </Card>

                  {usesActivePractice ? (
                    <div className="p-4 md:p-5">
                      <ActivePractice
                        key={lesson.id}
                        lesson={lesson}
                        onReadyChange={setActivePracticeReady}
                      />
                    </div>
                  ) : (
                    <div className="p-4 md:p-5">
                      <Questions
                        key={lesson.id}
                        lesson={lesson}
                        onAllCorrectChange={setQuizAllCorrect}
                      />
                    </div>
                  )}
                </div>

                <div className="sticky bottom-0 flex flex-col gap-3 border-t border-border bg-background/95 py-4 backdrop-blur md:flex-row md:items-center md:justify-end">
                  <Button
                    type="button"
                    className="w-full md:w-fit"
                    variant={lesson.completed ? "outline" : "default"}
                    disabled={
                      completeMutation.isPending || lesson.completed || !lessonId || !canComplete
                    }
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
              </div>
            </main>
          </div>
        </>
      ) : null}
    </div>
  )
}
