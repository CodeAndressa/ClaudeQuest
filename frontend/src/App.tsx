import { BrowserRouter, Route, Routes } from "react-router"

import { RequireAuth } from "@/features/auth/components/require-auth"
import { RequireGuest } from "@/features/auth/components/require-guest"
import { HealthPage } from "@/features/health/health-page"
import { DashboardPage } from "@/features/dashboard/pages/dashboard-page"
import { TracksPage } from "@/features/learning/pages/tracks-page"
import { TrackDetailPage } from "@/features/learning/pages/track-detail-page"
import { LessonPage } from "@/features/learning/pages/lesson-page"
import { PrivateLayout } from "@/layouts/private-layout"
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
              <PrivateLayout />
            </RequireAuth>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="tracks" element={<TracksPage />} />
          <Route path="tracks/:trackId" element={<TrackDetailPage />} />
          <Route path="tracks/:trackId/lessons/:lessonId" element={<LessonPage />} />
          <Route path="_status" element={<HealthPage />} />
        </Route>
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
