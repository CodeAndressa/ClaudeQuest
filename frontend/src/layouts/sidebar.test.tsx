import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { Sidebar } from "@/layouts/sidebar"
import * as authService from "@/services/auth-service"
import { useAuthStore } from "@/store/auth-store"
import { useThemeStore } from "@/store/theme-store"
import type { AuthenticatedUser } from "@/types/auth"

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
  useThemeStore.setState({ theme: "dark" })
  document.documentElement.classList.remove("light")
})

function renderSidebar(role: AuthenticatedUser["role"] = "student") {
  useAuthStore.setState({
    user: { id: "1", name: "Ana Souza", email: "ana@claudequest.dev", role },
  })

  return render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route path="/dashboard" element={<Sidebar />} />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>
  )
}

describe("Sidebar", () => {
  it("mostra o nome e o e-mail do usuário logado", () => {
    renderSidebar()

    expect(screen.getByText("Ana Souza")).toBeInTheDocument()
    expect(screen.getByText("ana@claudequest.dev")).toBeInTheDocument()
  })

  it("mostra o item de navegação do Dashboard como link funcional", () => {
    renderSidebar()

    const link = screen.getByRole("link", { name: /dashboard/i })
    expect(link).toHaveAttribute("href", "/dashboard")
  })

  it("mostra o item de navegação de Trilhas como link funcional", () => {
    renderSidebar()

    const link = screen.getByRole("link", { name: /trilhas/i })
    expect(link).toHaveAttribute("href", "/tracks")
  })

  it("mostra o item Admin como link funcional para usuario admin", () => {
    renderSidebar("admin")

    const link = screen.getByRole("link", { name: /admin/i })
    expect(link).toHaveAttribute("href", "/admin")
  })

  it("nao mostra o item Admin para usuario student", () => {
    renderSidebar("student")

    expect(screen.queryByRole("link", { name: /admin/i })).not.toBeInTheDocument()
  })

  it("mostra itens futuros (Ranking) como desabilitados, nunca como link", () => {
    renderSidebar()

    expect(screen.queryByRole("link", { name: /ranking/i })).not.toBeInTheDocument()

    const comingSoonLabels = screen.getAllByText(/em breve/i)
    expect(comingSoonLabels.length).toBeGreaterThanOrEqual(1)
  })

  it("alterna entre tema escuro e claro ao clicar no toggle de tema", async () => {
    renderSidebar()

    expect(document.documentElement.classList.contains("light")).toBe(false)

    await userEvent.click(screen.getByRole("button", { name: /mudar para o tema claro/i }))

    expect(useThemeStore.getState().theme).toBe("light")
    expect(document.documentElement.classList.contains("light")).toBe(true)

    await userEvent.click(screen.getByRole("button", { name: /mudar para o tema escuro/i }))

    expect(useThemeStore.getState().theme).toBe("dark")
    expect(document.documentElement.classList.contains("light")).toBe(false)
  })

  it("troca o idioma ao selecionar outro idioma no seletor", async () => {
    renderSidebar()

    const select = screen.getByLabelText(/idioma/i)
    await userEvent.selectOptions(select, "en-US")

    await waitFor(() => expect(i18n.language).toBe("en-US"))

    await userEvent.selectOptions(screen.getByLabelText(/language/i), "pt-BR")
    await waitFor(() => expect(i18n.language).toBe("pt-BR"))
  })

  it("faz logout, limpa a sessão e navega para /login ao clicar em Sair", async () => {
    const logoutSpy = vi.spyOn(authService, "logout").mockResolvedValue({ status: "ok" })

    render(
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route path="/dashboard" element={<Sidebar />} />
            <Route path="/login" element={<div>Tela de login</div>} />
          </Routes>
        </MemoryRouter>
      </I18nextProvider>
    )

    await userEvent.click(screen.getByRole("button", { name: /sair/i }))

    await waitFor(() => expect(screen.getByText(/tela de login/i)).toBeInTheDocument())
    expect(logoutSpy).toHaveBeenCalled()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("limpa a sessão e navega para /login mesmo se a chamada de logout falhar", async () => {
    vi.spyOn(authService, "logout").mockRejectedValue(new Error("network down"))

    render(
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route path="/dashboard" element={<Sidebar />} />
            <Route path="/login" element={<div>Tela de login</div>} />
          </Routes>
        </MemoryRouter>
      </I18nextProvider>
    )

    await userEvent.click(screen.getByRole("button", { name: /sair/i }))

    await waitFor(() => expect(screen.getByText(/tela de login/i)).toBeInTheDocument())
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it("chama onNavigate ao clicar em um item de navegação no modo mobile", async () => {
    const onNavigate = vi.fn()

    render(
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route path="/dashboard" element={<Sidebar isMobile onNavigate={onNavigate} />} />
          </Routes>
        </MemoryRouter>
      </I18nextProvider>
    )

    await userEvent.click(screen.getByRole("link", { name: /dashboard/i }))

    expect(onNavigate).toHaveBeenCalled()
  })

  it("mostra o botão de fechar quando renderizado no modo mobile", () => {
    render(
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route path="/dashboard" element={<Sidebar isMobile onNavigate={vi.fn()} />} />
          </Routes>
        </MemoryRouter>
      </I18nextProvider>
    )

    expect(screen.getByRole("button", { name: /fechar menu de navegação/i })).toBeInTheDocument()
  })
})
