import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useTranslation } from "react-i18next"
import { useMutation } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { login } from "@/services/auth-service"
import { useAuthStore } from "@/store/auth-store"
import { ApiError } from "@/types/api"
import { createLoginSchema, type LoginFormValues } from "@/features/auth/schemas/login-schema"

const ERROR_MESSAGE_KEYS: Record<string, string> = {
  invalid_credentials: "auth.login.errors.invalidCredentials",
  account_not_active: "auth.login.errors.accountNotActive",
}

export interface LoginFormProps {
  onSuccess: () => void
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const { t } = useTranslation()
  const setSession = useAuthStore((state) => state.setSession)
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(createLoginSchema(t)),
  })

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: (tokens) => {
      setFormError(null)
      setSession(tokens)
      onSuccess()
    },
    onError: (error: unknown) => {
      const key =
        error instanceof ApiError
          ? (ERROR_MESSAGE_KEYS[error.code] ?? "auth.login.errors.generic")
          : "auth.login.errors.generic"
      setFormError(t(key))
    },
  })

  const onSubmit = handleSubmit((values) => {
    setFormError(null)
    mutation.mutate(values)
  })

  return (
    <form onSubmit={onSubmit} noValidate className="flex w-full flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">{t("auth.login.emailLabel")}</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder={t("auth.login.emailPlaceholder")}
          aria-invalid={Boolean(errors.email)}
          {...register("email")}
        />
        {errors.email && (
          <p role="alert" className="text-sm text-destructive">
            {errors.email.message}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="password">{t("auth.login.passwordLabel")}</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          placeholder={t("auth.login.passwordPlaceholder")}
          aria-invalid={Boolean(errors.password)}
          {...register("password")}
        />
        {errors.password && (
          <p role="alert" className="text-sm text-destructive">
            {errors.password.message}
          </p>
        )}
      </div>

      {formError && (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      )}

      <Button type="submit" disabled={mutation.isPending} className="mt-2">
        {mutation.isPending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
        {t("auth.login.submit")}
      </Button>
    </form>
  )
}
