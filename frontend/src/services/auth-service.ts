import { apiPost } from "@/lib/api-client"
import type { TokenPair } from "@/types/auth"

export interface LoginPayload {
  email: string
  password: string
}

export function login(payload: LoginPayload): Promise<TokenPair> {
  return apiPost<TokenPair>("/auth/login", payload)
}
