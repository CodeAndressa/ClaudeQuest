import { z } from "zod"
import type { TFunction } from "i18next"

export function createLoginSchema(t: TFunction) {
  return z.object({
    email: z.email(t("auth.login.errors.emailInvalid")),
    password: z.string().min(1, t("auth.login.errors.passwordRequired")),
  })
}

export type LoginFormValues = z.infer<ReturnType<typeof createLoginSchema>>
