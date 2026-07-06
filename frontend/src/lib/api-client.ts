import { ApiError, type ApiResponse } from "@/types/api"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1"

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  const body = (await response.json()) as ApiResponse<T>

  if (!body.success) {
    throw new ApiError(body)
  }

  return body.data
}
