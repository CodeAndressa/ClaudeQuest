import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { MemoryRouter } from "react-router"
import { beforeAll, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { ForgotPasswordPage } from "@/features/auth/pages/forgot-password-page"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

describe("ForgotPasswordPage", () => {
  it("renderiza o título, o formulário e o link de volta ao login", () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <ForgotPasswordPage />
          </MemoryRouter>
        </QueryClientProvider>
      </I18nextProvider>
    )

    expect(screen.getByRole("heading", { name: /recuperar senha/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /voltar para o login/i })).toHaveAttribute(
      "href",
      "/login"
    )
  })
})
