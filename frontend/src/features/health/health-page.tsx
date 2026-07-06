import { useQuery } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import { Loader2, CheckCircle2, XCircle } from "lucide-react"

import { fetchHealth } from "@/services/health-service"
import { Button } from "@/components/ui/button"

export function HealthPage() {
  const { t } = useTranslation()
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  })

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-4 text-center text-foreground">
      <h1 className="text-2xl font-semibold">{t("health.title")}</h1>

      {isLoading && (
        <p className="flex items-center gap-2 text-muted-foreground" role="status">
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          {t("health.loading")}
        </p>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-3" role="alert">
          <p className="flex items-center gap-2 text-destructive">
            <XCircle className="size-4" aria-hidden="true" />
            {t("health.error")}
          </p>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? <Loader2 className="size-4 animate-spin" /> : null}
            {t("health.retry")}
          </Button>
        </div>
      )}

      {data && (
        <p className="flex flex-col items-center gap-1 text-success">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="size-4" aria-hidden="true" />
            {t("health.success")}
          </span>
          <span className="text-sm text-muted-foreground">
            {t("health.environment", { environment: data.environment })}
          </span>
        </p>
      )}
    </main>
  )
}
