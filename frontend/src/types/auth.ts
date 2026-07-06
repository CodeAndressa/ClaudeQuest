export interface AuthenticatedUser {
  id: string
  name: string
  email: string
  role: "student" | "admin"
}

/**
 * Resposta pública de login/refresh. O refresh token nunca aparece aqui:
 * ele é entregue exclusivamente via cookie httpOnly pelo backend (ver
 * backend/app/domains/auth/cookies.py) e nunca chega ao JavaScript do
 * frontend, para reduzir a superfície de roubo via XSS.
 */
export interface SessionResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthenticatedUser
}
