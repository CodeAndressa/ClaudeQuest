import { render, screen, waitFor } from "@testing-library/react"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { RequireGuest } from "@/features/auth/components/require-guest"
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

function renderGuestOnly() {
  return render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route
            path="/login"
            element={
              <RequireGuest>
                <div>Tela de login</div>
              </RequireGuest>
            }
          />
          <Route path="/" element={<div>Página inicial</div>} />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>
  )
}

describe("RequireGuest", () => {
  it("mostra o estado de carregamento enquanto o bootstrap está em andamento", () => {
    vi.spyOn(authService, "refresh").mockReturnValue(new Promise(() => {}))

    renderGuestOnly()

    expect(screen.getByRole("status")).toBeInTheDocument()
  })

  it("renderiza a tela de convidado quando o bootstrap resolve deslogado", async () => {
    vi.spyOn(authService, "refresh").mockRejectedValue(new Error("invalid_refresh_token"))

    renderGuestOnly()

    await waitFor(() => expect(screen.getByText(/tela de login/i)).toBeInTheDocument())
  })

  it("redireciona para / quando o bootstrap resolve autenticado", async () => {
    vi.spyOn(authService, "refresh").mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_in: 1800,
      user: { id: "1", name: "Ana", email: "ana@claudequest.dev", role: "student" },
    })

    renderGuestOnly()

    await waitFor(() => expect(screen.getByText(/página inicial/i)).toBeInTheDocument())
  })
})
