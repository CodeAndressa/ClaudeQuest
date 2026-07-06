import { useEffect, useState } from "react"
import { Outlet } from "react-router"
import { useTranslation } from "react-i18next"

import { MobileMenuTrigger, Sidebar } from "@/layouts/sidebar"

/**
 * Layout autenticado: sidebar fixa em telas médias/grandes (>= md) e menu
 * hambúrguer com painel deslizante em telas pequenas (mobile-first). Usa
 * <Outlet/> do react-router para renderizar as rotas filhas aninhadas.
 */
export function PrivateLayout() {
  const { t } = useTranslation()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Fecha o menu mobile automaticamente se a viewport crescer para desktop,
  // evitando um painel "preso" aberto atrás do layout desktop.
  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 768px)")
    function handleChange(event: MediaQueryListEvent) {
      if (event.matches) setIsMobileMenuOpen(false)
    }
    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [])

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden md:block md:w-64 md:shrink-0">
        <Sidebar />
      </aside>

      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <div
            className="fixed inset-0 bg-black/50"
            aria-hidden="true"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <div className="relative z-50 h-full w-72 max-w-[85vw]">
            <Sidebar isMobile onNavigate={() => setIsMobileMenuOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-border bg-card px-4 py-3 md:hidden">
          <MobileMenuTrigger onClick={() => setIsMobileMenuOpen(true)} />
          <span className="text-base font-semibold text-primary">{t("app.name")}</span>
        </header>

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
