import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthBootstrap } from "@/features/auth/hooks/use-auth-bootstrap"
import * as authService from "@/services/auth-service"
import { useAuthStore } from "@/store/auth-store"

beforeEach(() => {
  useAuthStore.setState({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isBootstrapping: true,
  })
})

describe("useAuthBootstrap", () => {
  it("restaura a sessão quando o refresh via cookie funciona", async () => {
    vi.spyOn(authService, "refresh").mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_in: 1800,
      user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
    })

    const { result } = renderHook(() => useAuthBootstrap())

    expect(result.current.isBootstrapping).toBe(true)

    await waitFor(() => expect(result.current.isBootstrapping).toBe(false))

    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(useAuthStore.getState().accessToken).toBe("token-abc")
  })

  it("trata falha no refresh como usuário deslogado, sem lançar erro", async () => {
    vi.spyOn(authService, "refresh").mockRejectedValue(new Error("invalid_refresh_token"))

    const { result } = renderHook(() => useAuthBootstrap())

    await waitFor(() => expect(result.current.isBootstrapping).toBe(false))

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("ignora o resultado do refresh se o componente desmontar antes dele resolver", async () => {
    let resolveRefresh: (value: Awaited<ReturnType<typeof authService.refresh>>) => void = () => {}
    vi.spyOn(authService, "refresh").mockReturnValue(
      new Promise((resolve) => {
        resolveRefresh = resolve
      })
    )

    const { unmount } = renderHook(() => useAuthBootstrap())
    unmount()

    resolveRefresh({
      access_token: "token-abc",
      token_type: "bearer",
      expires_in: 1800,
      user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
    })

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().isBootstrapping).toBe(true)
  })
})
