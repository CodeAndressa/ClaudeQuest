import { render, screen } from "@testing-library/react"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeEach, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { RequireAdmin } from "@/features/auth/components/require-admin"
import { useAuthStore } from "@/store/auth-store"
import type { AuthenticatedUser } from "@/types/auth"

function setUser(role: AuthenticatedUser["role"]) {
  useAuthStore.setState({
    user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role },
    accessToken: "token-abc",
    isAuthenticated: true,
    isBootstrapping: false,
  })
}

function renderRoute() {
  return render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter initialEntries={["/admin"]}>
        <Routes>
          <Route
            path="/admin"
            element={
              <RequireAdmin>
                <div>Admin liberado</div>
              </RequireAdmin>
            }
          />
          <Route path="/dashboard" element={<div>Dashboard do aluno</div>} />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>
  )
}

describe("RequireAdmin", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isBootstrapping: false,
    })
  })

  it("renderiza o conteudo quando o usuario e admin", () => {
    setUser("admin")

    renderRoute()

    expect(screen.getByText(/admin liberado/i)).toBeInTheDocument()
  })

  it("redireciona para o dashboard quando o usuario nao e admin", () => {
    setUser("student")

    renderRoute()

    expect(screen.getByText(/dashboard do aluno/i)).toBeInTheDocument()
  })
})
