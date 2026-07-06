import { useTranslation } from "react-i18next"
import { useQuery } from "@tanstack/react-query"
import { Trophy } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchRanking } from "@/features/dashboard/services/gamification-service"

export function RankingCard() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ["gamification", "ranking"],
    queryFn: fetchRanking,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Trophy className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.ranking.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {isLoading && (
          <span className="text-sm text-muted-foreground" role="status">
            {t("dashboard.loading")}
          </span>
        )}
        {!isLoading && !data?.current_user && (
          <span className="text-sm text-muted-foreground">{t("dashboard.ranking.empty")}</span>
        )}
        {!isLoading && data?.current_user && (
          <>
            <span className="text-3xl font-semibold text-foreground">
              {t("dashboard.ranking.position", { position: data.current_user.position })}
            </span>
            <span className="text-sm text-muted-foreground">
              {t("dashboard.ranking.totalUsers", { total: data.total_users })}
            </span>
          </>
        )}
      </CardContent>
    </Card>
  )
}
