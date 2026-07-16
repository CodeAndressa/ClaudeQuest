import { useMutation, useQuery } from "@tanstack/react-query"
import { Download, GraduationCap, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  downloadCertificate,
  fetchMyCertificates,
} from "@/features/dashboard/services/gamification-service"

export function CertificatesCard() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ["gamification", "me", "certificates"],
    queryFn: fetchMyCertificates,
  })
  const downloadMutation = useMutation({
    mutationFn: async ({ path, title }: { path: string; title: string }) => {
      const blob = await downloadCertificate(path)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = `${title.toLowerCase().replaceAll(" ", "-")}.pdf`
      anchor.click()
      URL.revokeObjectURL(url)
    },
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
        {isLoading ? (
          <span className="text-sm text-muted-foreground" role="status">
            {t("dashboard.loading")}
          </span>
        ) : null}
        {!isLoading && (!data || data.length === 0) ? (
          <span className="text-sm text-muted-foreground">{t("dashboard.certificates.empty")}</span>
        ) : null}
        {!isLoading && data && data.length > 0 ? (
          <ul className="flex flex-col divide-y divide-border">
            {data.map((certificate) => (
              <li
                key={certificate.id}
                className="flex flex-wrap items-center gap-3 py-3 first:pt-0 last:pb-0"
              >
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="text-sm font-medium text-foreground">{certificate.title}</span>
                  <span className="break-all text-xs text-muted-foreground">
                    {certificate.hours}h · {certificate.validation_code}
                  </span>
                </div>
                {certificate.pdf_url ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={downloadMutation.isPending}
                    onClick={() =>
                      downloadMutation.mutate({
                        path: certificate.pdf_url!,
                        title: certificate.title,
                      })
                    }
                  >
                    {downloadMutation.isPending ? (
                      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Download className="size-4" aria-hidden="true" />
                    )}
                    {t("dashboard.certificates.download")}
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        {downloadMutation.isError ? (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {t("dashboard.certificates.downloadError")}
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}
