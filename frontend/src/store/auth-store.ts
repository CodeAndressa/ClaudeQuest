import { create } from "zustand"
import { persist } from "zustand/middleware"

import type { AuthenticatedUser, SessionResponse } from "@/types/auth"

interface AuthState {
  user: AuthenticatedUser | null
  accessToken: string | null
  isAuthenticated: boolean
  /** true enquanto o bootstrap inicial (restaurar sessão via cookie) está em andamento. */
  isBootstrapping: boolean
  setSession: (session: SessionResponse) => void
  clearSession: () => void
  setBootstrapping: (value: boolean) => void
}

/**
 * O access token vive SÓ em memória (nunca em `persist`): ele nunca deve ir para
 * localStorage, para reduzir a superfície de roubo via XSS. O refresh token nem
 * chega ao JS - é um cookie httpOnly gerenciado pelo backend. Persistimos apenas
 * `user`, só para evitar flash de UI enquanto o bootstrap (refresh via cookie)
 * roda no carregamento da página; `isAuthenticated`/`accessToken` reais são
 * sempre recalculados a partir do refresh, nunca confiados a partir do cache.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isBootstrapping: true,
      setSession: (session) =>
        set({
          user: session.user,
          accessToken: session.access_token,
          isAuthenticated: true,
        }),
      clearSession: () => set({ user: null, accessToken: null, isAuthenticated: false }),
      setBootstrapping: (value) => set({ isBootstrapping: value }),
    }),
    {
      name: "claudequest-auth",
      partialize: (state) => ({ user: state.user }),
    }
  )
)
