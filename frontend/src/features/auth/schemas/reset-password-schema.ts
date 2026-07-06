import { z } from "zod"
import type { TFunction } from "i18next"

export function createResetPasswordSchema(t: TFunction) {
  return z
    .object({
      newPassword: z.string().min(8, t("auth.resetPassword.errors.tooShort")),
      confirmPassword: z.string().min(1, t("auth.resetPassword.errors.tooShort")),
    })
    .refine((values) => values.newPassword === values.confirmPassword, {
      message: t("auth.resetPassword.errors.mismatch"),
      path: ["confirmPassword"],
    })
}

export type ResetPasswordFormValues = z.infer<ReturnType<typeof createResetPasswordSchema>>
