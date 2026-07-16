import { act, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeAll, beforeEach, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { PrivateLayout } from "@/layouts/private-layout"
import { useAuthStore } from "@/store/auth-store"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

beforeEach(() => {
  useAuthStore.setState({
    user: { id: "1", name: "Ana Souza", email: "ana@claudequest.dev", role: "student" },
    accessToken: "token-abc",
    isAuthenticated: true,
    isBootstrapping: false,
  })
})

function renderLayout() {
  return render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route path="/" element={<PrivateLayout />}>
            <Route path="dashboard" element={<div>Conteúdo do dashboard</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </I18nextProvider>
  )
}

describe("PrivateLayout", () => {
  it("renderiza o conteúdo da rota filha via Outlet", () => {
    renderLayout()

    expect(screen.getByText(/conteúdo do dashboard/i)).toBeInTheDocument()
  })

  it("abre e fecha o menu mobile ao clicar no botão hambúrguer e depois em fechar", async () => {
    renderLayout()

    expect(
      screen.queryByRole("button", { name: /fechar menu de navegação/i })
    ).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: /abrir menu de navegação/i }))

    expect(screen.getByRole("button", { name: /fechar menu de navegação/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: /fechar menu de navegação/i }))

    expect(
      screen.queryByRole("button", { name: /fechar menu de navegação/i })
    ).not.toBeInTheDocument()
  })

  it("fecha o menu mobile ao clicar no overlay", async () => {
    renderLayout()

    await userEvent.click(screen.getByRole("button", { name: /abrir menu de navegação/i }))
    expect(screen.getByRole("button", { name: /fechar menu de navegação/i })).toBeInTheDocument()

    const overlay = document.querySelector(".bg-black\\/50")
    expect(overlay).not.toBeNull()
    await userEvent.click(overlay as Element)

    expect(
      screen.queryByRole("button", { name: /fechar menu de navegação/i })
    ).not.toBeInTheDocument()
  })

  it("renderiza o nome do app no header mobile", () => {
    renderLayout()

    const appNameMatches = screen.getAllByText("Vértice")
    expect(appNameMatches.length).toBeGreaterThan(0)
  })

  it("fecha o menu mobile automaticamente quando a viewport cresce para desktop", async () => {
    let changeListener: ((event: MediaQueryListEvent) => void) | undefined

    const originalMatchMedia = window.matchMedia
    window.matchMedia = ((query: string) =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: (_event: string, listener: (event: MediaQueryListEvent) => void) => {
          changeListener = listener
        },
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList) as typeof window.matchMedia

    try {
      renderLayout()

      await userEvent.click(screen.getByRole("button", { name: /abrir menu de navegação/i }))
      expect(screen.getByRole("button", { name: /fechar menu de navegação/i })).toBeInTheDocument()

      act(() => {
        changeListener?.({ matches: true } as MediaQueryListEvent)
      })

      expect(
        screen.queryByRole("button", { name: /fechar menu de navegação/i })
      ).not.toBeInTheDocument()
    } finally {
      window.matchMedia = originalMatchMedia
    }
  })
})
