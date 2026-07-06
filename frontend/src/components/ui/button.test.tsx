import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { Button } from "@/components/ui/button"

describe("Button", () => {
  it("renderiza um <button> por padrão", () => {
    render(<Button>Continuar</Button>)

    expect(screen.getByRole("button", { name: "Continuar" })).toBeInTheDocument()
  })

  it("renderiza o elemento filho quando asChild é usado", () => {
    render(
      <Button asChild>
        <a href="/proximo">Continuar</a>
      </Button>
    )

    expect(screen.getByRole("link", { name: "Continuar" })).toBeInTheDocument()
  })
})
