import { Link } from "react-router"
import { useTranslation } from "react-i18next"
import { BookOpen, ListChecks } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { TrackSummary } from "@/features/learning/types/learning"

export interface TrackCardProps {
  track: TrackSummary
}

const DIFFICULTY_COLOR: Record<string, string> = {
  beginner: "text-emerald-400",
  intermediate: "text-teal-400",
  advanced: "text-cyan-400",
  expert: "text-rose-400",
  master: "text-primary",
}

export function TrackCard({ track }: TrackCardProps) {
  const { t } = useTranslation()
  const progressLabel = t("tracks.progress", {
    completed: track.completed_lessons,
    total: track.total_lessons,
    percent: track.progress_percent,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="size-5 text-primary" aria-hidden="true" />
          {track.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="line-clamp-2 text-sm text-muted-foreground">{track.description}</p>
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span
            className={cn(
              "font-medium",
              DIFFICULTY_COLOR[track.difficulty] ?? "text-muted-foreground"
            )}
          >
            {t(`tracks.difficulty.${track.difficulty}`, { defaultValue: track.difficulty })}
          </span>
          <div className="flex items-center gap-3 text-muted-foreground">
            <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
              <ListChecks className="size-4 text-primary" aria-hidden="true" />
              {t("tracks.activitiesCount", { count: track.total_lessons })}
            </span>
            <span>{t("tracks.hours", { count: track.estimated_hours })}</span>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{progressLabel}</span>
            <span>{t("tracks.progressPercent", { percent: track.progress_percent })}</span>
          </div>
          <Progress value={track.progress_percent} aria-label={progressLabel} />
        </div>
        <Link
          to={`/tracks/${track.id}`}
          className={cn(buttonVariants({ variant: "default" }), "w-full")}
        >
          {t("tracks.viewCta")}
        </Link>
      </CardContent>
    </Card>
  )
}
