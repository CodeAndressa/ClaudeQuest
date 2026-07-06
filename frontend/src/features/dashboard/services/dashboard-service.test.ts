import { afterEach, describe, expect, it, vi } from "vitest"

import { fetchDashboard } from "@/features/dashboard/services/dashboard-service"

describe("fetchDashboard", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("busca o resumo do dashboard do backend", async () => {
    const dashboardData = {
      xp: { total: 120, level: 3, xp_to_next_level: 80 },
      streak: { current_days: 5, last_active_date: "2026-07-05" },
      ranking: { position: 12, total_users: 340 },
      next_lesson: {
        track_title: "Claude Chat",
        lesson_title: "Prompts eficazes",
        lesson_id: "lesson-1",
      },
      badges: [],
      certificates: [],
    }

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () =>
          Promise.resolve({
            success: true,
            message: "ok",
            data: dashboardData,
            metadata: { request_id: "abc", execution_time_ms: 1 },
          }),
      })
    )

    const result = await fetchDashboard()

    expect(result).toEqual(dashboardData)
  })
})
