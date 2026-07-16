import { apiGet, apiPatch, apiPost } from "@/lib/api-client"
import type {
  AdminCertificate,
  AdminOverview,
  AdminTrack,
  AdminUser,
  UserStatus,
} from "@/features/admin/types/admin"

export function fetchAdminOverview(): Promise<AdminOverview> {
  return apiGet<AdminOverview>("/admin/overview")
}

export function fetchAdminUsers(): Promise<AdminUser[]> {
  return apiGet<AdminUser[]>("/admin/users")
}

export function createAdminUser(payload: {
  name: string
  email: string
  password: string
  role: AdminUser["role"]
}): Promise<AdminUser> {
  return apiPost<AdminUser>("/admin/users", payload)
}

export function updateAdminUserStatus(userId: string, status: UserStatus): Promise<AdminUser> {
  return apiPatch<AdminUser>(`/admin/users/${userId}/status`, { status })
}

export function fetchAdminTracks(): Promise<AdminTrack[]> {
  return apiGet<AdminTrack[]>("/admin/tracks")
}

export function updateAdminTrackStatus(trackId: string, isActive: boolean): Promise<AdminTrack> {
  return apiPatch<AdminTrack>(`/admin/tracks/${trackId}/status`, { is_active: isActive })
}

export function fetchAdminCertificates(): Promise<AdminCertificate[]> {
  return apiGet<AdminCertificate[]>("/admin/certificates")
}
