import { useTranslation } from "react-i18next"
import { Flame } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { DashboardStreak } from "@/features/dashboard/types/dashboard"

export interface StreakCardProps {
  streak: DashboardStreak
}

export function StreakCard({ streak }: StreakCardProps) {
  const { t } = useTranslation()
  const hasStreak = streak.current_days > 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Flame className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.streak.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <span className="text-3xl font-semibold text-foreground">{streak.current_days}</span>
        <span className="text-sm text-muted-foreground">
          {hasStreak ? t("dashboard.streak.activeMessage") : t("dashboard.streak.emptyMessage")}
        </span>
      </CardContent>
    </Card>
  )
}
