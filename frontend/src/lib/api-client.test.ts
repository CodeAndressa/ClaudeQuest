import { afterEach, describe, expect, it, vi } from "vitest"

import { apiGet } from "@/lib/api-client"
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
