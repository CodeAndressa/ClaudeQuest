import { useTranslation } from "react-i18next"
import { useQuery } from "@tanstack/react-query"
import { GraduationCap } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchMyCertificates } from "@/features/dashboard/services/gamification-service"

export function CertificatesCard() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ["gamification", "me", "certificates"],
    queryFn: fetchMyCertificates,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GraduationCap className="size-5 text-primary" aria-hidden="true" />
          {t("dashboard.certificates.title")}
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
            {t("dashboard.certificates.comingSoon")}
          </span>
        )}
        {!isLoading && data && data.length > 0 && (
          <ul className="flex flex-col gap-2">
            {data.map((certificate) => (
              <li key={certificate.id} className="flex flex-col">
                <span className="text-sm font-medium text-foreground">{certificate.title}</span>
                <span className="text-xs text-muted-foreground">
                  {certificate.hours}h · {certificate.validation_code}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
