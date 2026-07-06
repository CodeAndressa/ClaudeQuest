import { apiGet } from "@/lib/api-client"
import type { DashboardSummary } from "@/features/dashboard/types/dashboard"

export function fetchDashboard(): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>("/dashboard/me")
}
