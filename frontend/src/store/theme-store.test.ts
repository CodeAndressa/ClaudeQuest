import { beforeEach, describe, expect, it } from "vitest"

import { useThemeStore } from "@/store/theme-store"

beforeEach(() => {
  useThemeStore.setState({ theme: "dark" })
  document.documentElement.classList.remove("light")
})

describe("useThemeStore", () => {
  it("começa com o tema escuro por padrão", () => {
    expect(useThemeStore.getState().theme).toBe("dark")
  })

  it("setTheme aplica a classe light no <html> quando o tema é claro", () => {
    useThemeStore.getState().setTheme("light")

    expect(useThemeStore.getState().theme).toBe("light")
    expect(document.documentElement.classList.contains("light")).toBe(true)
  })

  it("setTheme remove a classe light do <html> quando o tema é escuro", () => {
    useThemeStore.getState().setTheme("light")
    useThemeStore.getState().setTheme("dark")

    expect(useThemeStore.getState().theme).toBe("dark")
    expect(document.documentElement.classList.contains("light")).toBe(false)
  })

  it("toggleTheme alterna entre dark e light e ajusta a classe no <html>", () => {
    useThemeStore.getState().toggleTheme()
    expect(useThemeStore.getState().theme).toBe("light")
    expect(document.documentElement.classList.contains("light")).toBe(true)

    useThemeStore.getState().toggleTheme()
    expect(useThemeStore.getState().theme).toBe("dark")
    expect(document.documentElement.classList.contains("light")).toBe(false)
  })

  it("aplica a classe do tema persistido ao reidratar o storage", () => {
    const persistApi = useThemeStore.persist

    document.documentElement.classList.remove("light")
    // Simula o callback interno de reidratação chamando diretamente a função
    // registrada em onRehydrateStorage com um estado persistido "light".
    const optionsWithCallback = persistApi.getOptions() as {
      onRehydrateStorage?: (state: unknown) => ((state?: unknown) => void) | void
    }
    const onRehydrate = optionsWithCallback.onRehydrateStorage?.(undefined)
    onRehydrate?.({ theme: "light" })

    expect(document.documentElement.classList.contains("light")).toBe(true)
  })
})
