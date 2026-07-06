import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { ForgotPasswordForm } from "@/features/auth/components/forgot-password-form"
import * as authService from "@/services/auth-service"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

function renderForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <ForgotPasswordForm />
      </QueryClientProvider>
    </I18nextProvider>
  )
}

describe("ForgotPasswordForm", () => {
  it("mostra erro de validação para e-mail inválido", async () => {
    renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "nao-e-email")
    await userEvent.click(screen.getByRole("button", { name: /enviar link/i }))

    expect(await screen.findByText(/e-mail válido/i)).toBeInTheDocument()
  })

  it("mostra a mensagem de sucesso após enviar um e-mail válido", async () => {
    const forgotPasswordSpy = vi.spyOn(authService, "forgotPassword").mockResolvedValue({
      status: "ok",
    })
    renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.click(screen.getByRole("button", { name: /enviar link/i }))

    expect(await screen.findByText(/você vai receber um link/i)).toBeInTheDocument()
    expect(forgotPasswordSpy.mock.calls[0][0]).toEqual({ email: "ana@claudequest.dev" })
  })

  it("mostra erro genérico se a requisição falhar", async () => {
    vi.spyOn(authService, "forgotPassword").mockRejectedValue(new Error("network down"))
    renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.click(screen.getByRole("button", { name: /enviar link/i }))

    expect(await screen.findByRole("alert")).toBeInTheDocument()
  })

  it("desabilita o botão enquanto a requisição está pendente", async () => {
    vi.spyOn(authService, "forgotPassword").mockReturnValue(new Promise(() => {}))
    renderForm()

    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@claudequest.dev")
    await userEvent.click(screen.getByRole("button", { name: /enviar link/i }))

    expect(await screen.findByRole("button", { name: /enviar link/i })).toBeDisabled()
  })
})
