import { useQuery } from "@tanstack/react-query"
import { Link, useParams } from "react-router"
import { useTranslation } from "react-i18next"
import { AlertTriangle, ArrowLeft, CheckCircle2, Clock, Loader2 } from "lucide-react"

import { fetchTrackDetail } from "@/features/learning/services/learning-service"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import type { LevelDetail, ModuleDetail } from "@/features/learning/types/learning"

function TrackDetailSkeleton() {
  return (
    <div role="status" aria-busy="true" className="flex flex-col gap-4">
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-4 w-2/3" />
      {Array.from({ length: 3 }).map((_, index) => (
        <Card key={index}>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function LevelPath({ trackId, level }: { trackId: string; level: LevelDetail }) {
  const { t } = useTranslation()
  const lessons = [...level.lessons].sort((a, b) => a.order - b.order)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-medium text-foreground">{level.title}</h3>
        <span className="text-sm text-muted-foreground">
          {t("trackDetail.level", { number: level.level_number })}
        </span>
        <span className="text-sm text-muted-foreground">
          {t("trackDetail.xp", { count: level.xp })}
        </span>
      </div>

      <ol className="ml-2 flex flex-col gap-3 border-l-2 border-border pl-6">
        {lessons.map((lesson) => (
          <li key={lesson.id} className="relative">
            <span
              className={`absolute -left-[31px] top-3 flex size-4 items-center justify-center rounded-full border-2 ${
                lesson.completed
                  ? "border-emerald-400 bg-emerald-400 text-background"
                  : "border-primary bg-background"
              }`}
              aria-hidden="true"
            >
              {lesson.completed ? <CheckCircle2 className="size-3" /> : null}
            </span>
            <Link
              to={`/tracks/${trackId}/lessons/${lesson.id}`}
              className={`flex items-center justify-between gap-3 rounded-md border px-4 py-3 text-sm transition-colors duration-150 hover:bg-accent ${
                lesson.completed
                  ? "border-emerald-500/40 bg-emerald-500/10"
                  : "border-border bg-card"
              }`}
            >
              <span className="flex flex-col gap-1">
                <span className="font-medium text-foreground">{lesson.title}</span>
                {lesson.completed ? (
                  <span className="text-xs font-medium text-emerald-400">
                    {t("lesson.completedBadge")}
                  </span>
                ) : null}
              </span>
              <span className="flex shrink-0 items-center gap-1 text-muted-foreground">
                {lesson.completed ? (
                  <CheckCircle2 className="size-3.5 text-emerald-400" aria-hidden="true" />
                ) : null}
                <Clock className="size-3.5" aria-hidden="true" />
                {t("lesson.estimatedMinutes", { count: lesson.estimated_minutes })}
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  )
}

function ModuleSection({ trackId, module }: { trackId: string; module: ModuleDetail }) {
  const levels = [...module.levels].sort((a, b) => a.level_number - b.level_number)

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-medium leading-none tracking-tight text-foreground">
          {module.title}
        </h2>
        {module.description ? (
          <p className="text-sm text-muted-foreground">{module.description}</p>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {levels.map((level) => (
          <LevelPath key={level.id} trackId={trackId} level={level} />
        ))}
      </CardContent>
    </Card>
  )
}

export function TrackDetailPage() {
  const { t } = useTranslation()
  const { trackId } = useParams<{ trackId: string }>()
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["learning", "tracks", trackId],
    queryFn: () => fetchTrackDetail(trackId!),
  })

  const modules = data ? [...data.modules].sort((a, b) => a.order - b.order) : []
  const progressLabel = data
    ? t("trackDetail.progress", {
        completed: data.completed_lessons,
        total: data.total_lessons,
        percent: data.progress_percent,
      })
    : ""

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-8">
      <Link
        to="/tracks"
        className="flex w-fit items-center gap-2 text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        {t("trackDetail.back")}
      </Link>

      {isLoading && <TrackDetailSkeleton />}

      {isError && (
        <div className="flex flex-col items-center gap-3 py-12" role="alert">
          <p className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="size-4" aria-hidden="true" />
            {t("trackDetail.error")}
          </p>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
            {t("trackDetail.retry")}
          </Button>
        </div>
      )}

      {data && (
        <>
          <div className="flex flex-col gap-2">
            <h1 className="text-2xl font-semibold text-foreground">{data.title}</h1>
            <p className="text-sm text-muted-foreground">{data.description}</p>
            <div className="mt-2 flex flex-col gap-2">
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                <span>{progressLabel}</span>
                <span>{t("trackDetail.progressPercent", { percent: data.progress_percent })}</span>
              </div>
              <Progress value={data.progress_percent} aria-label={progressLabel} />
            </div>
          </div>

          {modules.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("trackDetail.modulesEmpty")}</p>
          ) : (
            <div className="flex flex-col gap-6">
              {modules.map((module) => (
                <ModuleSection key={module.id} trackId={trackId!} module={module} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
