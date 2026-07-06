import { ApiError, type ApiResponse } from "@/types/api"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1"

async function parseResponse<T>(response: Response): Promise<T> {
  const body = (await response.json()) as ApiResponse<T>

  if (!body.success) {
    throw new ApiError(body)
  }

  return body.data
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  return parseResponse<T>(response)
}

export async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  return parseResponse<T>(response)
}
