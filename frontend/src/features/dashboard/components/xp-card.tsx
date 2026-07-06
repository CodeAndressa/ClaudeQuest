import { useTranslation } from "react-i18next"
import { Sparkles } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import type { DashboardXp } from "@/features/dashboard/types/dashboard"

export interface XpCardProps {
  xp: DashboardXp
}

export function XpCard({ xp }: XpCardProps) {
  const { t } = useTranslation()

  const totalForLevel = xp.total + xp.xp_to_next_level
  const percent = totalForLevel > 0 ? (xp.total / totalForLevel) * 100 : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.xp.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between">
          <span className="text-3xl font-semibold text-foreground">{xp.total}</span>
          <span className="text-sm text-muted-foreground">
            {t("dashboard.xp.level", { level: xp.level })}
          </span>
        </div>
        <div className="flex flex-col gap-2">
          <Progress value={percent} aria-label={t("dashboard.xp.progressLabel")} />
          <span className="text-xs text-muted-foreground">
            {t("dashboard.xp.toNextLevel", { xp: xp.xp_to_next_level })}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
