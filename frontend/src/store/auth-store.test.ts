import { beforeEach, describe, expect, it } from "vitest"

import { useAuthStore } from "@/store/auth-store"
import type { SessionResponse } from "@/types/auth"

const session: SessionResponse = {
  access_token: "token-abc",
  token_type: "bearer",
  expires_in: 1800,
  user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
}

beforeEach(() => {
  useAuthStore.setState({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isBootstrapping: true,
  })
})

describe("useAuthStore", () => {
  it("começa deslogado e em bootstrap", () => {
    const state = useAuthStore.getState()

    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(state.isBootstrapping).toBe(true)
  })

  it("setSession guarda o usuário, o access token e marca como autenticado", () => {
    useAuthStore.getState().setSession(session)

    const state = useAuthStore.getState()
    expect(state.user).toEqual(session.user)
    expect(state.accessToken).toBe("token-abc")
    expect(state.isAuthenticated).toBe(true)
  })

  it("clearSession remove usuário e token e marca como não autenticado", () => {
    useAuthStore.getState().setSession(session)

    useAuthStore.getState().clearSession()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it("setBootstrapping alterna a flag de carregamento inicial", () => {
    useAuthStore.getState().setBootstrapping(false)

    expect(useAuthStore.getState().isBootstrapping).toBe(false)
  })

  it("persiste apenas o campo user no localStorage, nunca o access token", () => {
    useAuthStore.getState().setSession(session)

    const raw = window.localStorage.getItem("claudequest-auth")
    expect(raw).not.toBeNull()
    const persisted = JSON.parse(raw as string) as { state: Record<string, unknown> }

    expect(persisted.state).toHaveProperty("user")
    expect(persisted.state).not.toHaveProperty("accessToken")
    expect(persisted.state).not.toHaveProperty("refreshToken")
    expect(persisted.state).not.toHaveProperty("isAuthenticated")
  })
})
