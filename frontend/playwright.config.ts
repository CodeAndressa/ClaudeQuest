import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // Workers concorrentes demais causam "spawn UNKNOWN" ao lançar o Chromium neste ambiente.
  workers: 2,
  retries: process.env.CI ? 2 : 0,
  reporter: "html",
  use: {
    baseURL: "http://localhost:5180",
    locale: "pt-BR",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5180",
    reuseExistingServer: !process.env.CI,
  },
})
