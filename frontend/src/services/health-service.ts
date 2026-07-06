import { apiGet } from "@/lib/api-client"

export interface HealthStatus {
  app: string
  environment: string
  status: string
}

export function fetchHealth(): Promise<HealthStatus> {
  return apiGet<HealthStatus>("/health")
}
