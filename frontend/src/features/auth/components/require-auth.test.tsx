import { render, screen, waitFor } from "@testing-library/react"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { RequireAuth } from "@/features/auth/components/require-auth"
import * as authService from "@/services/auth-service"
import { useAuthStore } from "@/store/auth-store"

beforeEach(() => {
  useAuthStore.setState({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isBootstrapping: true,
  })
})

function renderProtected() {
  return render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route
            path="/"
            element={
              <RequireAuth>
                <div>Conteúdo protegido</div>
              </RequireAuth>
            }
          />
          <Route path="/login" element={<div>Tela de login</div>} />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>
  )
}

describe("RequireAuth", () => {
  it("mostra o estado de carregamento enquanto o bootstrap está em andamento", () => {
    vi.spyOn(authService, "refresh").mockReturnValue(new Promise(() => {}))

    renderProtected()

    expect(screen.getByRole("status")).toBeInTheDocument()
  })

  it("renderiza o conteúdo protegido quando o bootstrap resolve autenticado", async () => {
    vi.spyOn(authService, "refresh").mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_in: 1800,
      user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
    })

    renderProtected()

    await waitFor(() => expect(screen.getByText(/conteúdo protegido/i)).toBeInTheDocument())
  })

  it("redireciona para /login quando o bootstrap resolve deslogado", async () => {
    vi.spyOn(authService, "refresh").mockRejectedValue(new Error("invalid_refresh_token"))

    renderProtected()

    await waitFor(() => expect(screen.getByText(/tela de login/i)).toBeInTheDocument())
  })
})
