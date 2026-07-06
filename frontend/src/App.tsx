import { BrowserRouter, Route, Routes } from "react-router"

import { HealthPage } from "@/features/health/health-page"
import { LoginPage } from "@/features/auth/pages/login-page"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HealthPage />} />
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
