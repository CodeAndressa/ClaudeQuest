import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { I18nextProvider } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

import { AdminHomePage } from "@/features/admin/pages/admin-home-page"
import i18n from "@/i18n"

vi.mock("@/features/admin/services/admin-service", () => ({
  createAdminUser: vi.fn(),
  fetchAdminOverview: vi.fn().mockResolvedValue({
    users: 12,
    active_users: 10,
    tracks: 8,
    published_tracks: 7,
    lessons: 96,
    lesson_completions: 240,
    issued_certificates: 18,
    awarded_badges: 42,
  }),
  fetchAdminUsers: vi.fn().mockResolvedValue([]),
  fetchAdminTracks: vi.fn().mockResolvedValue([]),
  fetchAdminCertificates: vi.fn().mockResolvedValue([]),
  updateAdminUserStatus: vi.fn(),
  updateAdminTrackStatus: vi.fn(),
}))

beforeAll(async () => {
  await i18n.changeLanguage("pt-BR")
})

describe("AdminHomePage", () => {
  it("exibe indicadores operacionais no lugar de módulos planejados", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <I18nextProvider i18n={i18n}>
          <AdminHomePage />
        </I18nextProvider>
      </QueryClientProvider>
    )

    expect(screen.getByRole("heading", { name: /admin portal/i })).toBeInTheDocument()
    expect(screen.getByText(/administração operacional/i)).toBeInTheDocument()
    expect(await screen.findByText("96")).toBeInTheDocument()
    expect(screen.getByText("18")).toBeInTheDocument()
    expect(screen.queryByText(/planejado/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/próximo/i)).not.toBeInTheDocument()
  })
})
