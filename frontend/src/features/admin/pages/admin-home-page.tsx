import { useTranslation } from "react-i18next"
import {
  BarChart3,
  Bot,
  Award,
  Flag,
  Gamepad2,
  GraduationCap,
  ShieldCheck,
  Users,
} from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const MODULES = [
  { key: "users", icon: Users, status: "planned" },
  { key: "content", icon: GraduationCap, status: "next" },
  { key: "gamification", icon: Gamepad2, status: "planned" },
  { key: "ai", icon: Bot, status: "planned" },
  { key: "analytics", icon: BarChart3, status: "planned" },
  { key: "certificates", icon: Award, status: "planned" },
  { key: "settings", icon: ShieldCheck, status: "planned" },
  { key: "flags", icon: Flag, status: "planned" },
] as const

export function AdminHomePage() {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-8">
      <div className="flex max-w-3xl flex-col gap-2">
        <h1 className="text-2xl font-semibold text-foreground">{t("admin.title")}</h1>
        <p className="text-sm leading-6 text-muted-foreground">{t("admin.subtitle")}</p>
      </div>

      <section
        aria-label={t("admin.readiness.title")}
        className="rounded-lg border border-border bg-secondary px-4 py-4 text-secondary-foreground"
      >
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-medium text-foreground">{t("admin.readiness.title")}</h2>
            <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
              {t("admin.readiness.description")}
            </p>
          </div>
          <span className="w-fit rounded-md bg-background px-3 py-1 text-xs font-medium text-foreground">
            {t("admin.readiness.badge")}
          </span>
        </div>
      </section>

      <section aria-label={t("admin.modules.title")} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold text-foreground">{t("admin.modules.title")}</h2>
          <p className="text-sm text-muted-foreground">{t("admin.modules.description")}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {MODULES.map((module) => {
            const Icon = module.icon
            return (
              <Card key={module.key}>
                <CardHeader className="gap-3">
                  <div className="flex items-start justify-between gap-3">
                    <span className="flex size-9 items-center justify-center rounded-md bg-secondary text-primary">
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <span className="rounded-md bg-secondary px-2 py-1 text-xs text-muted-foreground">
                      {t(`admin.status.${module.status}`)}
                    </span>
                  </div>
                  <CardTitle>{t(`admin.modules.${module.key}.title`)}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {t(`admin.modules.${module.key}.description`)}
                  </p>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>
    </div>
  )
}
