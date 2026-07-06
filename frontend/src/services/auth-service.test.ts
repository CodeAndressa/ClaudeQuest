import { afterEach, describe, expect, it, vi } from "vitest"

import { login } from "@/services/auth-service"

describe("login", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("envia e-mail e senha e retorna o par de tokens", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () =>
          Promise.resolve({
            success: true,
            message: "ok",
            data: {
              access_token: "a",
              refresh_token: "b",
              token_type: "bearer",
              expires_in: 1800,
              user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
            },
            metadata: { request_id: "r1", execution_time_ms: 1 },
          }),
      })
    )

    const result = await login({ email: "ana@claudequest.dev", password: "senha-correta" })

    expect(result.access_token).toBe("a")
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/login"),
      expect.objectContaining({ method: "POST" })
    )
  })
})
