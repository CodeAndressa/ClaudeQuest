import type { ReactNode } from "react"
import { Navigate } from "react-router"

import { useAuthStore } from "@/store/auth-store"

export interface RequireAdminProps {
  children: ReactNode
}

export function RequireAdmin({ children }: RequireAdminProps) {
  const user = useAuthStore((state) => state.user)

  if (user?.role !== "admin") {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
