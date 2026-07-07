import { useMemo } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "react-router"
import { useTranslation } from "react-i18next"
import { AlertTriangle, ArrowLeft, CheckCircle2, Clock, Loader2, Sparkles } from "lucide-react"

import { completeLesson, fetchTrackDetail } from "@/features/learning/services/learning-service"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
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

function Questions({ lesson }: { lesson: LessonDetail }) {
  const { t } = useTranslation()

  if (lesson.questions.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold text-foreground">{t("lesson.questionsTitle")}</h2>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {lesson.questions.map((question) => {
          const alternatives = [...question.alternatives].sort((a, b) => a.order - b.order)

          return (
            <div key={question.id} className="flex flex-col gap-3">
              <p className="font-medium text-foreground">{question.question}</p>
              <div className="grid gap-2">
                {alternatives.map((alternative) => (
                  <div
                    key={alternative.id}
                    className="flex items-start gap-3 rounded-md border border-border bg-background px-3 py-2 text-sm"
                  >
                    {alternative.is_correct ? (
                      <CheckCircle2
                        className="mt-0.5 size-4 shrink-0 text-emerald-400"
                        aria-hidden="true"
                      />
                    ) : (
                      <span
                        className="mt-1.5 size-2 shrink-0 rounded-full bg-muted-foreground/60"
                        aria-hidden="true"
                      />
                    )}
                    <div className="flex flex-col gap-1">
                      <span className="text-foreground">{alternative.text}</span>
                      {alternative.feedback ? (
                        <span className="text-xs text-muted-foreground">
                          {alternative.feedback}
                        </span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
              {question.explanation ? (
                <p className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
                  {question.explanation}
                </p>
              ) : null}
            </div>
          )
        })}
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

          <Questions lesson={lesson} />

          <div className="flex flex-col gap-3">
            <Button
              type="button"
              className="w-full md:w-fit"
              variant={lesson.completed ? "outline" : "default"}
              disabled={completeMutation.isPending || lesson.completed || !lessonId}
              onClick={() => completeMutation.mutate()}
            >
              {completeMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              ) : null}
              {lesson.completed ? t("lesson.completedCta") : t("lesson.completeCta")}
            </Button>
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
