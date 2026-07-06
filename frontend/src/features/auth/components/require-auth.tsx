import type { ReactNode } from "react"
import { Navigate } from "react-router"
import { useTranslation } from "react-i18next"
import { Loader2 } from "lucide-react"

import { useAuthBootstrap } from "@/features/auth/hooks/use-auth-bootstrap"
import { useAuthStore } from "@/store/auth-store"

export interface RequireAuthProps {
  children: ReactNode
}

/**
 * Protege rotas autenticadas: enquanto o bootstrap de sessão (restauração via
 * cookie httpOnly) está em andamento, mostra um estado de carregamento. Depois
 * dele terminar, redireciona para /login se não houver sessão válida.
 */
export function RequireAuth({ children }: RequireAuthProps) {
  const { t } = useTranslation()
  const { isBootstrapping } = useAuthBootstrap()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (isBootstrapping) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-background text-muted-foreground"
        role="status"
      >
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        <span className="ml-2">{t("auth.bootstrap.loading")}</span>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
