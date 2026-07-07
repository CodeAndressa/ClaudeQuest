import { useState } from "react"
import { NavLink, useNavigate } from "react-router"
import { useTranslation } from "react-i18next"
import {
  LayoutDashboard,
  Map,
  Trophy,
  ShieldCheck,
  Moon,
  Sun,
  Languages,
  LogOut,
  Menu,
  X,
  Loader2,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/auth-store"
import { useThemeStore } from "@/store/theme-store"
import { logout as logoutRequest } from "@/services/auth-service"
import { Button } from "@/components/ui/button"
import { supportedLanguages, type SupportedLanguage } from "@/i18n"

interface NavItem {
  to: string
  labelKey: string
  icon: typeof LayoutDashboard
  disabled?: boolean
  adminOnly?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
  { to: "/tracks", labelKey: "nav.tracks", icon: Map },
  { to: "/admin", labelKey: "nav.admin", icon: ShieldCheck, adminOnly: true },
  { to: "/ranking", labelKey: "nav.ranking", icon: Trophy, disabled: true },
]

export interface SidebarProps {
  /** Quando true, o componente é exibido como painel de navegação mobile (com botão de fechar). */
  isMobile?: boolean
  onNavigate?: () => void
}

export function Sidebar({ isMobile = false, onNavigate }: SidebarProps) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const clearSession = useAuthStore((state) => state.clearSession)
  const theme = useThemeStore((state) => state.theme)
  const toggleTheme = useThemeStore((state) => state.toggleTheme)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logoutRequest()
    } catch {
      // Logout é idempotente no backend; se a chamada falhar (ex.: rede
      // instável), ainda assim encerramos a sessão localmente.
    } finally {
      clearSession()
      navigate("/login", { replace: true })
    }
  }

  function handleLanguageChange(event: React.ChangeEvent<HTMLSelectElement>) {
    void i18n.changeLanguage(event.target.value as SupportedLanguage)
  }

  return (
    <div
      className={cn(
        "flex h-full w-full flex-col justify-between bg-card text-card-foreground",
        !isMobile && "border-r border-border"
      )}
    >
      <div className="flex flex-col gap-6 overflow-y-auto p-4">
        <div className="flex items-center justify-between">
          <span className="text-lg font-semibold text-primary">{t("app.name")}</span>
          {isMobile && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onNavigate}
              aria-label={t("nav.closeMenu")}
            >
              <X className="size-5" aria-hidden="true" />
            </Button>
          )}
        </div>

        <nav aria-label={t("nav.dashboard")} className="flex flex-col gap-1">
          {NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "admin").map((item) => {
            const Icon = item.icon
            if (item.disabled) {
              return (
                <span
                  key={item.to}
                  aria-disabled="true"
                  className="flex cursor-not-allowed items-center justify-between rounded-md px-3 py-2 text-sm text-muted-foreground opacity-50"
                >
                  <span className="flex items-center gap-3">
                    <Icon className="size-4" aria-hidden="true" />
                    {t(item.labelKey)}
                  </span>
                  <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
                    {t("nav.comingSoon")}
                  </span>
                </span>
              )
            }

            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-foreground hover:bg-secondary"
                  )
                }
              >
                <Icon className="size-4" aria-hidden="true" />
                {t(item.labelKey)}
              </NavLink>
            )
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-4 border-t border-border p-4">
        <div className="flex items-center justify-between gap-2">
          <label htmlFor="sidebar-language-select" className="sr-only">
            {t("sidebar.language.label")}
          </label>
          <div className="flex flex-1 items-center gap-2 rounded-md border border-input bg-transparent px-2 py-1.5">
            <Languages className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <select
              id="sidebar-language-select"
              value={i18n.language}
              onChange={handleLanguageChange}
              className="w-full bg-transparent text-sm text-foreground focus:outline-none"
            >
              {supportedLanguages.map((lng) => (
                <option key={lng} value={lng} className="bg-card text-card-foreground">
                  {t(`sidebar.language.${lng}`)}
                </option>
              ))}
            </select>
          </div>

          <Button
            variant="outline"
            size="icon"
            onClick={toggleTheme}
            aria-label={
              theme === "dark" ? t("sidebar.theme.toggleToLight") : t("sidebar.theme.toggleToDark")
            }
          >
            {theme === "dark" ? (
              <Sun className="size-4" aria-hidden="true" />
            ) : (
              <Moon className="size-4" aria-hidden="true" />
            )}
          </Button>
        </div>

        <div
          className="flex items-center justify-between gap-2 rounded-md bg-secondary px-3 py-2"
          aria-label={t("sidebar.userMenu.label")}
        >
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-secondary-foreground">{user?.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void handleLogout()}
            disabled={isLoggingOut}
            aria-label={t("auth.logout")}
          >
            {isLoggingOut ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <LogOut className="size-4" aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

export function MobileMenuTrigger({ onClick }: { onClick: () => void }) {
  const { t } = useTranslation()
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={onClick}
      aria-label={t("nav.openMenu")}
      className="md:hidden"
    >
      <Menu className="size-5" aria-hidden="true" />
    </Button>
  )
}
