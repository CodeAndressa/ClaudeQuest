import { afterEach, describe, expect, it, vi } from "vitest"

import { forgotPassword, login, logout, refresh, resetPassword } from "@/services/auth-service"

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  }
}

describe("login", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("envia e-mail e senha e retorna a sessão", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(200, {
          success: true,
          message: "ok",
          data: {
            access_token: "a",
            token_type: "bearer",
            expires_in: 1800,
            user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
          },
          metadata: { request_id: "r1", execution_time_ms: 1 },
        })
      )
    )

    const result = await login({ email: "ana@claudequest.dev", password: "senha-correta" })

    expect(result.access_token).toBe("a")
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/login"),
      expect.objectContaining({ method: "POST" })
    )
  })
})

describe("refresh", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("chama POST /auth/refresh sem body e retorna a nova sessão", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        success: true,
        message: "ok",
        data: {
          access_token: "novo-token",
          token_type: "bearer",
          expires_in: 1800,
          user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
        },
        metadata: { request_id: "r2", execution_time_ms: 1 },
      })
    )
    vi.stubGlobal("fetch", fetchMock)

    const result = await refresh()

    expect(result.access_token).toBe("novo-token")
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toEqual(expect.stringContaining("/auth/refresh"))
    expect(init.method).toBe("POST")
    expect(init.credentials).toBe("include")
    expect(init.body).toBeUndefined()
  })

  it("propaga o erro quando o cookie de refresh é inválido", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(401, {
          success: false,
          error: { code: "invalid_refresh_token", message: "x", details: {} },
          trace_id: "t1",
          timestamp: "2026-01-01T00:00:00Z",
        })
      )
    )

    await expect(refresh()).rejects.toThrow()
  })
})

describe("logout", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("chama POST /auth/logout e retorna status ok", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        success: true,
        message: "ok",
        data: { status: "ok" },
        metadata: { request_id: "r3", execution_time_ms: 1 },
      })
    )
    vi.stubGlobal("fetch", fetchMock)

    const result = await logout()

    expect(result).toEqual({ status: "ok" })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toEqual(expect.stringContaining("/auth/logout"))
    expect(init.credentials).toBe("include")
  })
})

describe("forgotPassword", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("chama POST /auth/forgot-password com o e-mail informado", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        success: true,
        message: "ok",
        data: { status: "ok" },
        metadata: { request_id: "r4", execution_time_ms: 1 },
      })
    )
    vi.stubGlobal("fetch", fetchMock)

    const result = await forgotPassword({ email: "ana@claudequest.dev" })

    expect(result).toEqual({ status: "ok" })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toEqual(expect.stringContaining("/auth/forgot-password"))
    expect(init.body).toBe(JSON.stringify({ email: "ana@claudequest.dev" }))
  })
})

describe("resetPassword", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("chama POST /auth/reset-password com o token e a nova senha", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        success: true,
        message: "ok",
        data: { status: "ok" },
        metadata: { request_id: "r5", execution_time_ms: 1 },
      })
    )
    vi.stubGlobal("fetch", fetchMock)

    const result = await resetPassword({ token: "token-abc", new_password: "senha-nova-123" })

    expect(result).toEqual({ status: "ok" })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toEqual(expect.stringContaining("/auth/reset-password"))
    expect(init.body).toBe(JSON.stringify({ token: "token-abc", new_password: "senha-nova-123" }))
  })

  it("propaga o erro quando o token é inválido", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(400, {
          success: false,
          error: { code: "invalid_reset_token", message: "x", details: {} },
          trace_id: "t2",
          timestamp: "2026-01-01T00:00:00Z",
        })
      )
    )

    await expect(
      resetPassword({ token: "invalido", new_password: "senha-nova-123" })
    ).rejects.toThrow()
  })
})
