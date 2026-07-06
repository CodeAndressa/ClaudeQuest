import { afterEach, describe, expect, it, vi } from "vitest"

import { fetchHealth } from "@/services/health-service"

describe("fetchHealth", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("busca o status de saúde do backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () =>
          Promise.resolve({
            success: true,
            message: "ok",
            data: { app: "ClaudeQuest", environment: "development", status: "ok" },
            metadata: { request_id: "abc", execution_time_ms: 1 },
          }),
      })
    )

    const result = await fetchHealth()

    expect(result).toEqual({ app: "ClaudeQuest", environment: "development", status: "ok" })
  })
})
