import { create } from "zustand"
import { persist } from "zustand/middleware"

import type { AuthenticatedUser, TokenPair } from "@/types/auth"

interface AuthState {
  user: AuthenticatedUser | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setSession: (tokens: TokenPair) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setSession: (tokens) =>
        set({
          user: tokens.user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isAuthenticated: true,
        }),
      clearSession: () =>
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),
    }),
    { name: "claudequest-auth" }
  )
)
