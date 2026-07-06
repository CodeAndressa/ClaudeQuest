import { useEffect } from "react"

import { refresh } from "@/services/auth-service"
import { useAuthStore } from "@/store/auth-store"

/**
 * Tenta restaurar a sessão a partir do cookie httpOnly refresh_token ao montar
 * o app. Isso é necessário porque o access token vive só em memória (nunca em
 * localStorage) — a cada carregamento de página, ele precisa ser reobtido via
 * /auth/refresh. Se falhar (cookie ausente/expirado/revogado), trata como
 * usuário deslogado, sem exibir erro na tela.
 */
export function useAuthBootstrap(): { isBootstrapping: boolean } {
  const isBootstrapping = useAuthStore((state) => state.isBootstrapping)
  const setSession = useAuthStore((state) => state.setSession)
  const clearSession = useAuthStore((state) => state.clearSession)
  const setBootstrapping = useAuthStore((state) => state.setBootstrapping)

  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      try {
        const session = await refresh()
        if (!cancelled) {
          setSession(session)
        }
      } catch {
        if (!cancelled) {
          clearSession()
        }
      } finally {
        if (!cancelled) {
          setBootstrapping(false)
        }
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [setSession, clearSession, setBootstrapping])

  return { isBootstrapping }
}
