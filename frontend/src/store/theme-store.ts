import { create } from "zustand"
import { persist } from "zustand/middleware"

export type Theme = "dark" | "light"

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

// Dark Mode é o padrão obrigatório do produto (02 - UX/UX.md.md); Light é opcional.
export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set({ theme: get().theme === "dark" ? "light" : "dark" }),
    }),
    { name: "claudequest-theme" }
  )
)
