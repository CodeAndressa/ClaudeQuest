import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "@/index.css"
import "@/i18n"
import App from "@/App"
import { QueryProvider } from "@/providers/query-provider"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryProvider>
      <App />
    </QueryProvider>
  </StrictMode>
)
