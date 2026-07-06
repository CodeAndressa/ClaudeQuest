import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"

import ptBR from "@/i18n/locales/pt-BR/common.json"
import enUS from "@/i18n/locales/en-US/common.json"
import esES from "@/i18n/locales/es-ES/common.json"

export const supportedLanguages = ["pt-BR", "en-US", "es-ES"] as const
export type SupportedLanguage = (typeof supportedLanguages)[number]

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      "pt-BR": { common: ptBR },
      "en-US": { common: enUS },
      "es-ES": { common: esES },
    },
    fallbackLng: "pt-BR",
    supportedLngs: supportedLanguages,
    defaultNS: "common",
    interpolation: { escapeValue: false },
  })

export default i18n
