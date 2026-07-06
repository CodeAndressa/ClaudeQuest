import { afterEach, describe, expect, it, vi } from "vitest"

import {
  fetchMyBadges,
  fetchMyCertificates,
  fetchRanking,
} from "@/features/dashboard/services/gamification-service"

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: () => Promise.resolve(body) }
}

const successBody = (data: unknown) => ({
  success: true,
  message: "ok",
  data,
  metadata: { request_id: "abc", execution_time_ms: 1 },
})

describe("fetchMyBadges", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("busca os badges do usuário logado", async () => {
    const badges = [
      {
        id: "ub1",
        badge_id: "b1",
        earned_at: "2026-07-06T00:00:00Z",
        badge: {
          id: "b1",
          name: "Primeiro Login",
          description: "x",
          image: null,
          category: "bronze",
        },
      },
    ]
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(successBody(badges))))

    const result = await fetchMyBadges()

    expect(result).toEqual(badges)
  })
})

describe("fetchMyCertificates", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("busca os certificados do usuário logado", async () => {
    const certificates = [
      {
        id: "uc1",
        certificate_id: "c1",
        title: "Certificado Claude Chat",
        hours: 4,
        validation_code: "codigo-123",
        issued_at: "2026-07-06T00:00:00Z",
        pdf_url: null,
      },
    ]
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(successBody(certificates))))

    const result = await fetchMyCertificates()

    expect(result).toEqual(certificates)
  })
})

describe("fetchRanking", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("busca o ranking global", async () => {
    const ranking = {
      top: [{ user_id: "1", name: "Eu", score: 720, position: 1 }],
      current_user: { user_id: "1", name: "Eu", score: 720, position: 1 },
      total_users: 1,
    }
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(successBody(ranking))))

    const result = await fetchRanking()

    expect(result).toEqual(ranking)
  })
})
