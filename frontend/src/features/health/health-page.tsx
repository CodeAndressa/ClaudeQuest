import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router"
import { useTranslation } from "react-i18next"
import { Loader2, CheckCircle2, XCircle } from "lucide-react"

import { fetchHealth } from "@/services/health-service"
import { logout } from "@/services/auth-service"
import { useAuthStore } from "@/store/auth-store"
import { Button } from "@/components/ui/button"

export function HealthPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const clearSession = useAuthStore((state) => state.clearSession)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  })

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logout()
    } catch {
      // Logout é idempotente no backend; se a chamada falhar (ex.: rede
      // instável), ainda assim encerramos a sessão localmente.
    } finally {
      clearSession()
      navigate("/login", { replace: true })
    }
  }

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-4 text-center text-foreground">
      <Button
        variant="outline"
        className="absolute right-4 top-4"
        onClick={() => void handleLogout()}
        disabled={isLoggingOut}
      >
        {isLoggingOut && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
        {t("auth.logout")}
      </Button>

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
