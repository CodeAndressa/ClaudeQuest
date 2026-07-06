import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useTranslation } from "react-i18next"
import { useMutation } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { resetPassword } from "@/services/auth-service"
import { ApiError } from "@/types/api"
import {
  createResetPasswordSchema,
  type ResetPasswordFormValues,
} from "@/features/auth/schemas/reset-password-schema"

const ERROR_MESSAGE_KEYS: Record<string, string> = {
  invalid_reset_token: "auth.resetPassword.errors.invalidToken",
}

export interface ResetPasswordFormProps {
  token: string
  onSuccess: () => void
}

export function ResetPasswordForm({ token, onSuccess }: ResetPasswordFormProps) {
  const { t } = useTranslation()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(createResetPasswordSchema(t)),
  })

  const mutation = useMutation({
    mutationFn: (values: ResetPasswordFormValues) =>
      resetPassword({ token, new_password: values.newPassword }),
    onSuccess: () => {
      setFormError(null)
      onSuccess()
    },
    onError: (error: unknown) => {
      const key =
        error instanceof ApiError
          ? (ERROR_MESSAGE_KEYS[error.code] ?? "auth.resetPassword.errors.generic")
          : "auth.resetPassword.errors.generic"
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
        <Label htmlFor="newPassword">{t("auth.resetPassword.newPasswordLabel")}</Label>
        <Input
          id="newPassword"
          type="password"
          autoComplete="new-password"
          placeholder={t("auth.resetPassword.newPasswordPlaceholder")}
          aria-invalid={Boolean(errors.newPassword)}
          {...register("newPassword")}
        />
        {errors.newPassword && (
          <p role="alert" className="text-sm text-destructive">
            {errors.newPassword.message}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="confirmPassword">{t("auth.resetPassword.confirmPasswordLabel")}</Label>
        <Input
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          placeholder={t("auth.resetPassword.confirmPasswordPlaceholder")}
          aria-invalid={Boolean(errors.confirmPassword)}
          {...register("confirmPassword")}
        />
        {errors.confirmPassword && (
          <p role="alert" className="text-sm text-destructive">
            {errors.confirmPassword.message}
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
        {t("auth.resetPassword.submit")}
      </Button>
    </form>
  )
}
