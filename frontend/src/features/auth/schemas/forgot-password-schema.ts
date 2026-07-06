import { z } from "zod"
import type { TFunction } from "i18next"

export function createForgotPasswordSchema(t: TFunction) {
  return z.object({
    email: z.email(t("auth.login.errors.emailInvalid")),
  })
}

export type ForgotPasswordFormValues = z.infer<ReturnType<typeof createForgotPasswordSchema>>
