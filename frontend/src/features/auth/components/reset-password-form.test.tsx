import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { ResetPasswordForm } from "@/features/auth/components/reset-password-form"
import * as authService from "@/services/auth-service"
import { ApiError } from "@/types/api"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

function renderForm(onSuccess = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <ResetPasswordForm token="token-abc" onSuccess={onSuccess} />
      </QueryClientProvider>
    </I18nextProvider>
  )
  return { onSuccess }
}

describe("ResetPasswordForm", () => {
  it("mostra erro de validação para senha curta", async () => {
    renderForm()

    await userEvent.type(screen.getByLabelText(/^nova senha$/i), "curta")
    await userEvent.type(screen.getByLabelText(/confirmar nova senha/i), "curta")
    await userEvent.click(screen.getByRole("button", { name: /salvar nova senha/i }))

    expect(await screen.findByText(/pelo menos 8 caracteres/i)).toBeInTheDocument()
  })

  it("mostra erro de validação quando as senhas não coincidem", async () => {
    renderForm()

    await userEvent.type(screen.getByLabelText(/^nova senha$/i), "senha-nova-123")
    await userEvent.type(screen.getByLabelText(/confirmar nova senha/i), "outra-senha-456")
    await userEvent.click(screen.getByRole("button", { name: /salvar nova senha/i }))

    expect(await screen.findByText(/não coincidem/i)).toBeInTheDocument()
  })

  it("chama onSuccess quando a troca de senha funciona", async () => {
    const resetPasswordSpy = vi.spyOn(authService, "resetPassword").mockResolvedValue({
      status: "ok",
    })
    const { onSuccess } = renderForm()

    await userEvent.type(screen.getByLabelText(/^nova senha$/i), "senha-nova-123")
    await userEvent.type(screen.getByLabelText(/confirmar nova senha/i), "senha-nova-123")
    await userEvent.click(screen.getByRole("button", { name: /salvar nova senha/i }))

    expect(onSuccess).toHaveBeenCalled()
    expect(resetPasswordSpy).toHaveBeenCalledWith({
      token: "token-abc",
      new_password: "senha-nova-123",
    })
  })

  it("mostra mensagem de token inválido quando o backend rejeita", async () => {
    vi.spyOn(authService, "resetPassword").mockRejectedValue(
      new ApiError({
        success: false,
        error: { code: "invalid_reset_token", message: "x", details: {} },
        trace_id: "t1",
        timestamp: "2026-01-01T00:00:00Z",
      })
    )
    renderForm()

    await userEvent.type(screen.getByLabelText(/^nova senha$/i), "senha-nova-123")
    await userEvent.type(screen.getByLabelText(/confirmar nova senha/i), "senha-nova-123")
    await userEvent.click(screen.getByRole("button", { name: /salvar nova senha/i }))

    expect(await screen.findByText(/inválido ou expirou/i)).toBeInTheDocument()
  })
})
