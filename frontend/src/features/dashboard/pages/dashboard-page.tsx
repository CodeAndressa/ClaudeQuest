import { useQuery } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import { AlertTriangle, Loader2 } from "lucide-react"

import { fetchDashboard } from "@/features/dashboard/services/dashboard-service"
import { XpCard } from "@/features/dashboard/components/xp-card"
import { StreakCard } from "@/features/dashboard/components/streak-card"
import { RankingCard } from "@/features/dashboard/components/ranking-card"
import { NextLessonCard } from "@/features/dashboard/components/next-lesson-card"
import { BadgesCard } from "@/features/dashboard/components/badges-card"
import { CertificatesCard } from "@/features/dashboard/components/certificates-card"
import { AchievementsCard } from "@/features/dashboard/components/achievements-card"
import { DashboardSkeleton } from "@/features/dashboard/components/dashboard-skeleton"
import { Button } from "@/components/ui/button"

export function DashboardPage() {
  const { t } = useTranslation()
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["dashboard", "me"],
    queryFn: fetchDashboard,
  })

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-8">
      <h1 className="text-2xl font-semibold text-foreground">{t("dashboard.title")}</h1>

      {isLoading && <DashboardSkeleton />}

      {isError && (
        <div className="flex flex-col items-center gap-3 py-12" role="alert">
          <p className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="size-4" aria-hidden="true" />
            {t("dashboard.error")}
          </p>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
            {t("dashboard.retry")}
          </Button>
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <XpCard xp={data.xp} />
          <StreakCard streak={data.streak} />
          <RankingCard />
          <NextLessonCard nextLesson={data.next_lesson} />
          <BadgesCard />
          <CertificatesCard />
          <AchievementsCard />
        </div>
      )}
    </div>
  )
}
