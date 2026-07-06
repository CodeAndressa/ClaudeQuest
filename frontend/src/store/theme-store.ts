import { create } from "zustand"
import { persist } from "zustand/middleware"

export type Theme = "dark" | "light"

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

/**
 * Aplica a classe `.light` no elemento <html> quando o tema for claro.
 * Ausência da classe (comportamento padrão) mantém o tema escuro, que é
 * obrigatório segundo a UX.md (Dark Mode obrigatório; Light Mode opcional).
 */
function applyThemeClass(theme: Theme) {
  if (typeof document === "undefined") return
  document.documentElement.classList.toggle("light", theme === "light")
}

// Dark Mode é o padrão obrigatório do produto (02 - UX/UX.md.md); Light é opcional.
export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme) => {
        applyThemeClass(theme)
        set({ theme })
      },
      toggleTheme: () => {
        const nextTheme = get().theme === "dark" ? "light" : "dark"
        applyThemeClass(nextTheme)
        set({ theme: nextTheme })
      },
    }),
    {
      name: "claudequest-theme",
      onRehydrateStorage: () => (state) => {
        if (state) applyThemeClass(state.theme)
      },
    }
  )
)
