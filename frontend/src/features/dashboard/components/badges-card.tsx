import { useTranslation } from "react-i18next"
import { Award } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function BadgesCard() {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Award className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.badges.title")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <span className="text-sm text-muted-foreground">{t("dashboard.badges.comingSoon")}</span>
      </CardContent>
    </Card>
  )
}
