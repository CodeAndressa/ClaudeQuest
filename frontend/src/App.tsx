import { BrowserRouter, Route, Routes } from "react-router"

import { RequireAuth } from "@/features/auth/components/require-auth"
import { RequireGuest } from "@/features/auth/components/require-guest"
import { HealthPage } from "@/features/health/health-page"
import { LoginPage } from "@/features/auth/pages/login-page"
import { ForgotPasswordPage } from "@/features/auth/pages/forgot-password-page"
import { ResetPasswordPage } from "@/features/auth/pages/reset-password-page"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <RequireAuth>
              <HealthPage />
            </RequireAuth>
          }
        />
        <Route
          path="/login"
          element={
            <RequireGuest>
              <LoginPage />
            </RequireGuest>
          }
        />
        <Route
          path="/forgot-password"
          element={
            <RequireGuest>
              <ForgotPasswordPage />
            </RequireGuest>
          }
        />
        <Route
          path="/reset-password"
          element={
            <RequireGuest>
              <ResetPasswordPage />
            </RequireGuest>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
