import { render, screen } from "@testing-library/react"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { AdminHomePage } from "@/features/admin/pages/admin-home-page"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

describe("AdminHomePage", () => {
  it("mostra o shell inicial do Admin Portal com modulos planejados", () => {
    render(
      <I18nextProvider i18n={i18n}>
        <AdminHomePage />
      </I18nextProvider>
    )

    expect(screen.getByRole("heading", { name: /admin portal/i })).toBeInTheDocument()
    expect(screen.getByText(/acesso admin ativo/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /conteúdo/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /usuários/i })).toBeInTheDocument()
    expect(screen.getAllByText(/planejado/i).length).toBeGreaterThan(1)
  })
})
