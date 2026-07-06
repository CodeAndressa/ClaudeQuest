import { useTranslation } from "react-i18next"
import { GraduationCap } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function CertificatesCard() {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GraduationCap className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.certificates.title")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <span className="text-sm text-muted-foreground">
          {t("dashboard.certificates.comingSoon")}
        </span>
      </CardContent>
    </Card>
  )
}
