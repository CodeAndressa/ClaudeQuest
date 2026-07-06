import { apiPost } from "@/lib/api-client"
import type { SessionResponse } from "@/types/auth"

export interface LoginPayload {
  email: string
  password: string
}

export function login(payload: LoginPayload): Promise<SessionResponse> {
  return apiPost<SessionResponse>("/auth/login", payload)
}

/** Renova a sessão a partir do cookie httpOnly refresh_token (enviado automaticamente). */
export function refresh(): Promise<SessionResponse> {
  return apiPost<SessionResponse>("/auth/refresh", undefined)
}

/** Revoga a sessão no backend e limpa o cookie httpOnly. Idempotente. */
export function logout(): Promise<{ status: string }> {
  return apiPost<{ status: string }>("/auth/logout", undefined)
}

export interface ForgotPasswordPayload {
  email: string
}

/** Sempre resolve com sucesso — o backend nunca revela se o e-mail existe. */
export function forgotPassword(payload: ForgotPasswordPayload): Promise<{ status: string }> {
  return apiPost<{ status: string }>("/auth/forgot-password", payload)
}

export interface ResetPasswordPayload {
  token: string
  new_password: string
}

export function resetPassword(payload: ResetPasswordPayload): Promise<{ status: string }> {
  return apiPost<{ status: string }>("/auth/reset-password", payload)
}
