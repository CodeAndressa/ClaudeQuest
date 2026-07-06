export interface AuthenticatedUser {
  id: string
  name: string
  email: string
  role: "student" | "admin"
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: AuthenticatedUser
}
