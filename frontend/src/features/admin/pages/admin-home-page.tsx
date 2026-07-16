import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Award,
  BookOpenCheck,
  CheckCircle2,
  GraduationCap,
  Loader2,
  ShieldCheck,
  UserPlus,
  Users,
} from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  createAdminUser,
  fetchAdminCertificates,
  fetchAdminOverview,
  fetchAdminTracks,
  fetchAdminUsers,
  updateAdminTrackStatus,
  updateAdminUserStatus,
} from "@/features/admin/services/admin-service"
import type { UserStatus } from "@/features/admin/types/admin"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/auth-store"

type AdminSection = "overview" | "users" | "tracks" | "certificates"

const SECTIONS = [
  { key: "overview", icon: ShieldCheck },
  { key: "users", icon: Users },
  { key: "tracks", icon: GraduationCap },
  { key: "certificates", icon: Award },
] as const

function LoadingState() {
  const { t } = useTranslation()
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-muted-foreground" role="status">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {t("admin.loading")}
    </div>
  )
}

function ErrorState() {
  const { t } = useTranslation()
  return <p className="py-10 text-sm text-destructive">{t("admin.error")}</p>
}

function OverviewSection() {
  const { t } = useTranslation()
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin", "overview"],
    queryFn: fetchAdminOverview,
  })
  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState />

  const metrics = [
    ["users", data.users, `${data.active_users} ${t("admin.overview.active")}`],
    ["tracks", data.tracks, `${data.published_tracks} ${t("admin.overview.published")}`],
    ["lessons", data.lessons, `${data.lesson_completions} ${t("admin.overview.completions")}`],
    [
      "certificates",
      data.issued_certificates,
      `${data.awarded_badges} ${t("admin.overview.badges")}`,
    ],
  ] as const

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map(([key, value, detail]) => (
        <Card key={key}>
          <CardContent className="flex flex-col gap-1 pt-6">
            <span className="text-sm text-muted-foreground">{t(`admin.overview.${key}`)}</span>
            <span className="text-2xl font-semibold text-foreground">{value}</span>
            <span className="text-xs text-muted-foreground">{detail}</span>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function UsersSection() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const currentUserId = useAuthStore((state) => state.user?.id)
  const [showForm, setShowForm] = useState(false)
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: fetchAdminUsers,
  })
  const mutation = useMutation({
    mutationFn: ({ userId, status }: { userId: string; status: UserStatus }) =>
      updateAdminUserStatus(userId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin"] })
    },
  })
  const createMutation = useMutation({
    mutationFn: createAdminUser,
    onSuccess: () => {
      setShowForm(false)
      void queryClient.invalidateQueries({ queryKey: ["admin"] })
    },
  })
  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState />

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">{t("admin.users.createHint")}</p>
        <Button type="button" onClick={() => setShowForm((value) => !value)}>
          <UserPlus className="size-4" aria-hidden="true" />
          {showForm ? t("admin.users.cancelCreate") : t("admin.users.create")}
        </Button>
      </div>

      {showForm ? (
        <form
          className="grid gap-4 rounded-lg border border-border bg-secondary/40 p-4 md:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault()
            const form = new FormData(event.currentTarget)
            createMutation.mutate({
              name: String(form.get("name")),
              email: String(form.get("email")),
              password: String(form.get("password")),
              role: String(form.get("role")) as "admin" | "student",
            })
          }}
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="admin-user-name">{t("admin.users.name")}</Label>
            <Input id="admin-user-name" name="name" required minLength={2} autoComplete="name" />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="admin-user-email">{t("admin.users.email")}</Label>
            <Input id="admin-user-email" name="email" type="email" required autoComplete="email" />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="admin-user-password">{t("admin.users.password")}</Label>
            <Input
              id="admin-user-password"
              name="password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="admin-user-role">{t("admin.users.role")}</Label>
            <select
              id="admin-user-role"
              name="role"
              defaultValue="student"
              className="h-10 rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="student">{t("admin.role.student")}</option>
              <option value="admin">{t("admin.role.admin")}</option>
            </select>
          </div>
          <div className="flex items-center gap-3 md:col-span-2">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? t("admin.users.creating") : t("admin.users.save")}
            </Button>
            {createMutation.isError ? (
              <span className="text-sm text-destructive">{t("admin.users.createError")}</span>
            ) : null}
          </div>
        </form>
      ) : null}

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-secondary text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">{t("admin.users.person")}</th>
              <th className="px-4 py-3 font-medium">{t("admin.users.role")}</th>
              <th className="px-4 py-3 font-medium">{t("admin.users.progress")}</th>
              <th className="px-4 py-3 font-medium">{t("admin.users.status")}</th>
              <th className="px-4 py-3 font-medium">{t("admin.users.actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.map((user) => (
              <tr key={user.id}>
                <td className="px-4 py-3">
                  <div className="font-medium text-foreground">{user.name}</div>
                  <div className="text-xs text-muted-foreground">{user.email}</div>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{t(`admin.role.${user.role}`)}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {t("admin.users.progressValue", {
                    lessons: user.completed_lessons,
                    certificates: user.certificates,
                  })}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-md bg-secondary px-2 py-1 text-xs text-foreground">
                    {t(`admin.userStatus.${user.status}`)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {(["active", "inactive", "blocked"] as const).map((status) => (
                      <Button
                        key={status}
                        type="button"
                        size="sm"
                        variant={user.status === status ? "secondary" : "ghost"}
                        disabled={mutation.isPending || user.id === currentUserId}
                        onClick={() => mutation.mutate({ userId: user.id, status })}
                      >
                        {t(`admin.userStatus.${status}`)}
                      </Button>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {mutation.isError ? <ErrorState /> : null}
      </div>
    </div>
  )
}

function TracksSection() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin", "tracks"],
    queryFn: fetchAdminTracks,
  })
  const mutation = useMutation({
    mutationFn: ({ trackId, active }: { trackId: string; active: boolean }) =>
      updateAdminTrackStatus(trackId, active),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin"] })
      void queryClient.invalidateQueries({ queryKey: ["learning", "tracks"] })
    },
  })
  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState />

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="bg-secondary text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">{t("admin.tracks.track")}</th>
            <th className="px-4 py-3 font-medium">{t("admin.tracks.content")}</th>
            <th className="px-4 py-3 font-medium">{t("admin.tracks.completions")}</th>
            <th className="px-4 py-3 font-medium">{t("admin.tracks.visibility")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((track) => (
            <tr key={track.id}>
              <td className="px-4 py-3">
                <div className="font-medium text-foreground">{track.title}</div>
                <div className="text-xs text-muted-foreground">
                  {t("admin.tracks.hours", { hours: track.estimated_hours })}
                </div>
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {t("admin.tracks.lessons", { count: track.lessons })}
              </td>
              <td className="px-4 py-3 text-muted-foreground">{track.completions}</td>
              <td className="px-4 py-3">
                <Button
                  type="button"
                  size="sm"
                  variant={track.is_active ? "outline" : "default"}
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate({ trackId: track.id, active: !track.is_active })}
                >
                  {track.is_active ? t("admin.tracks.unpublish") : t("admin.tracks.publish")}
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {mutation.isError ? <ErrorState /> : null}
    </div>
  )
}

function CertificatesSection() {
  const { t, i18n } = useTranslation()
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin", "certificates"],
    queryFn: fetchAdminCertificates,
  })
  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState />
  if (data.length === 0) {
    return <p className="py-10 text-sm text-muted-foreground">{t("admin.certificates.empty")}</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="bg-secondary text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">{t("admin.certificates.certificate")}</th>
            <th className="px-4 py-3 font-medium">{t("admin.certificates.student")}</th>
            <th className="px-4 py-3 font-medium">{t("admin.certificates.issued")}</th>
            <th className="px-4 py-3 font-medium">{t("admin.certificates.code")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((certificate) => (
            <tr key={certificate.id}>
              <td className="px-4 py-3 font-medium text-foreground">{certificate.title}</td>
              <td className="px-4 py-3">
                <div className="text-foreground">{certificate.user_name}</div>
                <div className="text-xs text-muted-foreground">{certificate.user_email}</div>
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {new Intl.DateTimeFormat(i18n.language).format(new Date(certificate.issued_at))}
              </td>
              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                {certificate.validation_code}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function AdminHomePage() {
  const { t } = useTranslation()
  const [activeSection, setActiveSection] = useState<AdminSection>("overview")

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-8">
      <div className="flex max-w-3xl flex-col gap-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="size-5 text-success" aria-hidden="true" />
          <span className="text-sm font-medium text-success">{t("admin.operational")}</span>
        </div>
        <h1 className="text-2xl font-semibold text-foreground">{t("admin.title")}</h1>
        <p className="text-sm leading-6 text-muted-foreground">{t("admin.subtitleOperational")}</p>
      </div>

      <nav
        className="flex gap-1 overflow-x-auto border-b border-border"
        aria-label={t("admin.nav")}
      >
        {SECTIONS.map((section) => {
          const Icon = section.icon
          const selected = activeSection === section.key
          return (
            <button
              key={section.key}
              type="button"
              aria-current={selected ? "page" : undefined}
              onClick={() => setActiveSection(section.key)}
              className={cn(
                "flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors",
                selected
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              {t(`admin.section.${section.key}`)}
            </button>
          )
        })}
      </nav>

      <section aria-label={t(`admin.section.${activeSection}`)}>
        {activeSection === "overview" ? <OverviewSection /> : null}
        {activeSection === "users" ? <UsersSection /> : null}
        {activeSection === "tracks" ? <TracksSection /> : null}
        {activeSection === "certificates" ? <CertificatesSection /> : null}
      </section>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <BookOpenCheck className="size-4" aria-hidden="true" />
        {t("admin.auditNote")}
      </div>
    </div>
  )
}
