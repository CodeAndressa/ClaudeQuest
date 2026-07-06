import { render, screen } from "@testing-library/react"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { XpCard } from "@/features/dashboard/components/xp-card"

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

describe("XpCard", () => {
  it("calcula o percentual de progresso com base no xp total e no xp para o próximo nível", () => {
    render(
      <I18nextProvider i18n={i18n}>
        <XpCard xp={{ total: 120, level: 3, xp_to_next_level: 80 }} />
      </I18nextProvider>
    )

    expect(screen.getByText("120")).toBeInTheDocument()
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "60")
  })

  it("não quebra quando o total para o nível é zero", () => {
    render(
      <I18nextProvider i18n={i18n}>
        <XpCard xp={{ total: 0, level: 1, xp_to_next_level: 0 }} />
      </I18nextProvider>
    )

    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0")
  })
})
