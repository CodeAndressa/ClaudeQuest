import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { apiGet, apiPost } from "@/lib/api-client"
import { useAuthStore } from "@/store/auth-store"
import { ApiError } from "@/types/api"

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  }
}

const successBody = (data: unknown) => ({
  success: true,
  message: "ok",
  data,
  metadata: { request_id: "abc", execution_time_ms: 1 },
})

const errorBody = (code: string) => ({
  success: false,
  error: { code, message: "x", details: {} },
  trace_id: "trace-1",
  timestamp: "2026-01-01T00:00:00Z",
})

beforeEach(() => {
  useAuthStore.setState({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isBootstrapping: false,
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("apiGet", () => {
  it("retorna data quando a resposta tem success=true", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(200, successBody({ status: "ok" })))
    )

    const result = await apiGet<{ status: string }>("/health")

    expect(result).toEqual({ status: "ok" })
  })

  it("lança ApiError quando a resposta tem success=false", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(422, errorBody("not_found"))))

    await expect(apiGet("/missing")).rejects.toBeInstanceOf(ApiError)
  })

  it("envia a requisição com credentials: include", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, successBody({ status: "ok" })))
    vi.stubGlobal("fetch", fetchMock)

    await apiGet("/health")

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.objectContaining({ credentials: "include" })
    )
  })

  it("anexa o header Authorization quando há access token no store", async () => {
    useAuthStore.setState({ accessToken: "token-123" })
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, successBody({ status: "ok" })))
    vi.stubGlobal("fetch", fetchMock)

    await apiGet("/health")

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const headers = new Headers(init.headers)
    expect(headers.get("Authorization")).toBe("Bearer token-123")
  })

  it("não anexa o header Authorization quando não há access token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, successBody({ status: "ok" })))
    vi.stubGlobal("fetch", fetchMock)

    await apiGet("/health")

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const headers = new Headers(init.headers)
    expect(headers.has("Authorization")).toBe(false)
  })

  it("tenta renovar a sessão em um 401, atualiza o token e repete a chamada original", async () => {
    useAuthStore.setState({ accessToken: "token-expirado", isAuthenticated: true })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, errorBody("unauthorized")))
      .mockResolvedValueOnce(
        jsonResponse(
          200,
          successBody({
            access_token: "token-novo",
            token_type: "bearer",
            expires_in: 1800,
            user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
          })
        )
      )
      .mockResolvedValueOnce(jsonResponse(200, successBody({ status: "ok" })))
    vi.stubGlobal("fetch", fetchMock)

    const result = await apiGet<{ status: string }>("/protected")

    expect(result).toEqual({ status: "ok" })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[1][0]).toEqual(expect.stringContaining("/auth/refresh"))
    expect(useAuthStore.getState().accessToken).toBe("token-novo")

    const [, retryInit] = fetchMock.mock.calls[2] as [string, RequestInit]
    const headers = new Headers(retryInit.headers)
    expect(headers.get("Authorization")).toBe("Bearer token-novo")
  })

  it("limpa a sessão e propaga o erro quando o refresh também falha", async () => {
    useAuthStore.setState({
      accessToken: "token-expirado",
      isAuthenticated: true,
      user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
    })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, errorBody("unauthorized")))
      .mockResolvedValueOnce(jsonResponse(401, errorBody("invalid_refresh_token")))
    vi.stubGlobal("fetch", fetchMock)

    await expect(apiGet("/protected")).rejects.toBeInstanceOf(ApiError)

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("limpa a sessão quando o refresh lança um erro de rede", async () => {
    useAuthStore.setState({ accessToken: "token-expirado", isAuthenticated: true })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, errorBody("unauthorized")))
      .mockRejectedValueOnce(new Error("network down"))
    vi.stubGlobal("fetch", fetchMock)

    await expect(apiGet("/protected")).rejects.toBeInstanceOf(ApiError)

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it("não tenta renovar a sessão quando o 401 vem de uma rota de auth", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(401, errorBody("invalid_refresh_token")))
    vi.stubGlobal("fetch", fetchMock)

    await expect(apiGet("/auth/refresh")).rejects.toBeInstanceOf(ApiError)

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("limpa a sessão quando o refresh responde 200 mas com success=false no corpo", async () => {
    useAuthStore.setState({ accessToken: "token-expirado", isAuthenticated: true })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, errorBody("unauthorized")))
      .mockResolvedValueOnce(jsonResponse(200, errorBody("invalid_refresh_token")))
    vi.stubGlobal("fetch", fetchMock)

    await expect(apiGet("/protected")).rejects.toBeInstanceOf(ApiError)

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})

describe("apiPost", () => {
  it("envia o payload via POST com JSON e retorna data em caso de sucesso", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, successBody({ created: true })))
    vi.stubGlobal("fetch", fetchMock)

    const result = await apiPost<{ created: boolean }>("/things", { name: "x" })

    expect(result).toEqual({ created: true })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toEqual(expect.stringContaining("/things"))
    expect(init.method).toBe("POST")
    expect(init.body).toBe(JSON.stringify({ name: "x" }))
    expect(init.credentials).toBe("include")
  })

  it("envia POST sem body quando nenhum payload é passado", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, successBody({ status: "ok" })))
    vi.stubGlobal("fetch", fetchMock)

    await apiPost("/auth/logout")

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.body).toBeUndefined()
  })

  it("lança ApiError quando a resposta do POST tem success=false", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(401, errorBody("invalid_credentials")))
    )

    await expect(apiPost("/auth/login", {})).rejects.toBeInstanceOf(ApiError)
  })
})
