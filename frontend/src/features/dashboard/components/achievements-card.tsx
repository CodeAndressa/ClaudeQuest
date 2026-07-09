import { useTranslation } from "react-i18next"
import { useQuery } from "@tanstack/react-query"
import { Crown, Flame, Footprints, Gem, Medal, Trophy, type LucideIcon } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchMyAchievements } from "@/features/dashboard/services/gamification-service"

const ICON_BY_NAME: Record<string, LucideIcon> = {
  footprints: Footprints,
  medal: Medal,
  flame: Flame,
  gem: Gem,
  crown: Crown,
}

export function AchievementsCard() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ["gamification", "me", "achievements"],
    queryFn: fetchMyAchievements,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Trophy className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.achievements.title")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <span className="text-sm text-muted-foreground" role="status">
            {t("dashboard.loading")}
          </span>
        )}
        {!isLoading && (!data || data.length === 0) && (
          <span className="text-sm text-muted-foreground">
            {t("dashboard.achievements.comingSoon")}
          </span>
        )}
        {!isLoading && data && data.length > 0 && (
          <ul className="flex flex-wrap gap-3">
            {data.map((userAchievement) => {
              const Icon = ICON_BY_NAME[userAchievement.achievement.icon] ?? Trophy
              return (
                <li
                  key={userAchievement.id}
                  className="flex flex-col items-center gap-1 text-center"
                  title={userAchievement.achievement.description}
                >
                  <Icon className="size-6 text-primary" aria-hidden="true" />
                  <span className="text-xs text-muted-foreground">
                    {userAchievement.achievement.name}
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
