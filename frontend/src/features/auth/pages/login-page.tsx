import { useNavigate } from "react-router"
import { useTranslation } from "react-i18next"

import { LoginForm } from "@/features/auth/components/login-form"

export function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="flex w-full max-w-sm flex-col gap-6 rounded-lg border border-border bg-card p-8">
        <div className="flex flex-col gap-1 text-center">
          <h1 className="text-xl font-semibold text-foreground">{t("auth.login.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("auth.login.subtitle")}</p>
        </div>

        <LoginForm onSuccess={() => navigate("/", { replace: true })} />
      </div>
    </main>
  )
}
