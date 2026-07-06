import { useState } from "react"
import { Link, useSearchParams } from "react-router"
import { useTranslation } from "react-i18next"
import { CheckCircle2 } from "lucide-react"

import { ResetPasswordForm } from "@/features/auth/components/reset-password-form"

export function ResetPasswordPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token")
  const [isDone, setIsDone] = useState(false)

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="flex w-full max-w-sm flex-col gap-6 rounded-lg border border-border bg-card p-8">
        <div className="flex flex-col gap-1 text-center">
          <h1 className="text-xl font-semibold text-foreground">{t("auth.resetPassword.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("auth.resetPassword.subtitle")}</p>
        </div>

        {!token && (
          <p role="alert" className="text-center text-sm text-destructive">
            {t("auth.resetPassword.missingToken")}
          </p>
        )}

        {token && isDone && (
          <p className="flex items-center gap-2 text-sm text-success" role="status">
            <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
            {t("auth.resetPassword.success")}
          </p>
        )}

        {token && !isDone && <ResetPasswordForm token={token} onSuccess={() => setIsDone(true)} />}

        <Link to="/login" className="text-center text-sm text-muted-foreground underline">
          {isDone ? t("auth.resetPassword.goToLogin") : t("auth.forgotPassword.backToLogin")}
        </Link>
      </div>
    </main>
  )
}
