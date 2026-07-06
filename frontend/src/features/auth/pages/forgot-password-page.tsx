import { Link } from "react-router"
import { useTranslation } from "react-i18next"

import { ForgotPasswordForm } from "@/features/auth/components/forgot-password-form"

export function ForgotPasswordPage() {
  const { t } = useTranslation()

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="flex w-full max-w-sm flex-col gap-6 rounded-lg border border-border bg-card p-8">
        <div className="flex flex-col gap-1 text-center">
          <h1 className="text-xl font-semibold text-foreground">
            {t("auth.forgotPassword.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("auth.forgotPassword.subtitle")}</p>
        </div>

        <ForgotPasswordForm />

        <Link to="/login" className="text-center text-sm text-muted-foreground underline">
          {t("auth.forgotPassword.backToLogin")}
        </Link>
      </div>
    </main>
  )
}
