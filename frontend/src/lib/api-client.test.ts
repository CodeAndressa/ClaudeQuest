import { afterEach, describe, expect, it, vi } from "vitest"

import { apiGet, apiPost } from "@/lib/api-client"
import { ApiError } from "@/types/api"

describe("apiGet", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("retorna data quando a resposta tem success=true", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () =>
          Promise.resolve({
            success: true,
            message: "ok",
            data: { status: "ok" },
            metadata: { request_id: "abc", execution_time_ms: 1.2 },
          }),
      })
    )

    const result = await apiGet<{ status: string }>("/health")

    expect(result).toEqual({ status: "ok" })
  })

  it("lança ApiError quando a resposta tem success=false", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () =>
          Promise.resolve({
            success: false,
            error: { code: "not_found", message: "não encontrado", details: {} },
            trace_id: "trace-1",
            timestamp: "2026-01-01T00:00:00Z",
          }),
      })
    )

    await expect(apiGet("/missing")).rejects.toBeInstanceOf(ApiError)
  })
})

describe("apiPost", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("envia o payload via POST com JSON e retorna data em caso de sucesso", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: () =>
        Promise.resolve({
          success: true,
          message: "ok",
          data: { created: true },
          metadata: { request_id: "abc", execution_time_ms: 1 },
        }),
    })
    vi.stubGlobal("fetch", fetchMock)

    const result = await apiPost<{ created: boolean }>("/things", { name: "x" })

    expect(result).toEqual({ created: true })
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/things"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "x" }),
      })
    )
  })

  it("lança ApiError quando a resposta do POST tem success=false", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () =>
          Promise.resolve({
            success: false,
            error: { code: "invalid_credentials", message: "x", details: {} },
            trace_id: "trace-2",
            timestamp: "2026-01-01T00:00:00Z",
          }),
      })
    )

    await expect(apiPost("/auth/login", {})).rejects.toBeInstanceOf(ApiError)
  })
})
