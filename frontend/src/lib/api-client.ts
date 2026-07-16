import { ApiError, type ApiResponse } from "@/types/api"
import { useAuthStore } from "@/store/auth-store"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1"

/**
 * Rotas de autenticação que nunca disparam o fluxo de retry-em-401: elas já
 * são as próprias rotas responsáveis por obter/renovar/encerrar a sessão, e
 * tentar "refresh" a partir de um 401 nelas causaria loop ou comportamento
 * incorreto (ex.: um /auth/login com credenciais erradas não deve acionar
 * /auth/refresh).
 */
const AUTH_ROUTES_WITHOUT_RETRY = ["/auth/login", "/auth/refresh", "/auth/logout"]

async function parseResponse<T>(response: Response): Promise<T> {
  const body = (await response.json()) as ApiResponse<T>

  if (!body.success) {
    throw new ApiError(body)
  }

  return body.data
}

function buildHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra)
  const accessToken = useAuthStore.getState().accessToken
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`)
  }
  return headers
}

function isRetryableAuthFailure(path: string, response: Response): boolean {
  return response.status === 401 && !AUTH_ROUTES_WITHOUT_RETRY.includes(path)
}

async function tryRefreshSession(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })

    if (!response.ok) {
      return false
    }

    const body = (await response.json()) as ApiResponse<{ access_token: string }>
    if (!body.success) {
      return false
    }

    useAuthStore.setState({ accessToken: body.data.access_token, isAuthenticated: true })
    return true
  } catch {
    return false
  }
}

async function requestWithRetry(path: string, init: RequestInit): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: buildHeaders(init.headers),
  })

  if (!isRetryableAuthFailure(path, response)) {
    return response
  }

  const refreshed = await tryRefreshSession()
  if (!refreshed) {
    useAuthStore.getState().clearSession()
    return response
  }

  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: buildHeaders(init.headers),
  })
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await requestWithRetry(path, { method: "GET" })
  return parseResponse<T>(response)
}

export async function apiPost<T>(path: string, payload?: unknown): Promise<T> {
  const response = await requestWithRetry(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  })
  return parseResponse<T>(response)
}

export async function apiPatch<T>(path: string, payload: unknown): Promise<T> {
  const response = await requestWithRetry(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  return parseResponse<T>(response)
}

export async function apiDownload(path: string): Promise<Blob> {
  const response = await requestWithRetry(path, { method: "GET" })
  if (!response.ok) {
    throw new Error(`Download failed with status ${response.status}`)
  }
  return response.blob()
}
