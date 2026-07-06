import { useTranslation } from "react-i18next"
import { useQuery } from "@tanstack/react-query"
import { Award } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchMyBadges } from "@/features/dashboard/services/gamification-service"

const CATEGORY_COLOR: Record<string, string> = {
  bronze: "text-amber-700",
  prata: "text-slate-300",
  ouro: "text-amber-400",
  platina: "text-cyan-300",
  diamante: "text-sky-300",
  lendario: "text-primary",
}

export function BadgesCard() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ["gamification", "me", "badges"],
    queryFn: fetchMyBadges,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Award className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.badges.title")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <span className="text-sm text-muted-foreground" role="status">
            {t("dashboard.loading")}
          </span>
        )}
        {!isLoading && (!data || data.length === 0) && (
          <span className="text-sm text-muted-foreground">{t("dashboard.badges.comingSoon")}</span>
        )}
        {!isLoading && data && data.length > 0 && (
          <ul className="flex flex-wrap gap-3">
            {data.map((userBadge) => (
              <li
                key={userBadge.id}
                className="flex flex-col items-center gap-1 text-center"
                title={userBadge.badge.description}
              >
                <Award
                  className={`size-6 ${CATEGORY_COLOR[userBadge.badge.category] ?? "text-primary"}`}
                  aria-hidden="true"
                />
                <span className="text-xs text-muted-foreground">{userBadge.badge.name}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
