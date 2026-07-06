import { useTranslation } from "react-i18next"
import { Trophy } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { DashboardRanking } from "@/features/dashboard/types/dashboard"

export interface RankingCardProps {
  ranking: DashboardRanking
}

export function RankingCard({ ranking }: RankingCardProps) {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Trophy className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.ranking.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {ranking.position === null ? (
          <span className="text-sm text-muted-foreground">{t("dashboard.ranking.empty")}</span>
        ) : (
          <>
            <span className="text-3xl font-semibold text-foreground">
              {t("dashboard.ranking.position", { position: ranking.position })}
            </span>
            <span className="text-sm text-muted-foreground">
              {t("dashboard.ranking.totalUsers", { total: ranking.total_users })}
            </span>
          </>
        )}
      </CardContent>
    </Card>
  )
}
