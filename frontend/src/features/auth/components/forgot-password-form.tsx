import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useTranslation } from "react-i18next"
import { useMutation } from "@tanstack/react-query"
import { Loader2, CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { forgotPassword } from "@/services/auth-service"
import {
  createForgotPasswordSchema,
  type ForgotPasswordFormValues,
} from "@/features/auth/schemas/forgot-password-schema"

export function ForgotPasswordForm() {
  const { t } = useTranslation()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(createForgotPasswordSchema(t)),
  })

  const mutation = useMutation({ mutationFn: forgotPassword })

  const onSubmit = handleSubmit((values) => {
    mutation.mutate(values)
  })

  if (mutation.isSuccess) {
    return (
      <p className="flex items-center gap-2 text-sm text-success" role="status">
        <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
        {t("auth.forgotPassword.success")}
      </p>
    )
  }

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

      {mutation.isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("auth.resetPassword.errors.generic")}
        </p>
      )}

      <Button type="submit" disabled={mutation.isPending} className="mt-2">
        {mutation.isPending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
        {t("auth.forgotPassword.submit")}
      </Button>
    </form>
  )
}
