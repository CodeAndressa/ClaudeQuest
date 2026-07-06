import { useQuery } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import { AlertTriangle, Loader2 } from "lucide-react"

import { fetchTracks } from "@/features/learning/services/learning-service"
import { TrackCard } from "@/features/learning/components/track-card"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"

function TracksSkeleton() {
  return (
    <div
      role="status"
      aria-busy="true"
      className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
    >
      {Array.from({ length: 6 }).map((_, index) => (
        <Card key={index}>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-9 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function TracksPage() {
  const { t } = useTranslation()
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["learning", "tracks"],
    queryFn: fetchTracks,
  })

  const tracks = data ? [...data].sort((a, b) => a.order - b.order) : []

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-8">
      <h1 className="text-2xl font-semibold text-foreground">{t("tracks.title")}</h1>

      {isLoading && <TracksSkeleton />}

      {isError && (
        <div className="flex flex-col items-center gap-3 py-12" role="alert">
          <p className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="size-4" aria-hidden="true" />
            {t("tracks.error")}
          </p>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
            {t("tracks.retry")}
          </Button>
        </div>
      )}

      {data && tracks.length === 0 && (
        <p className="text-sm text-muted-foreground">{t("tracks.empty")}</p>
      )}

      {data && tracks.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tracks.map((track) => (
            <TrackCard key={track.id} track={track} />
          ))}
        </div>
      )}
    </div>
  )
}
