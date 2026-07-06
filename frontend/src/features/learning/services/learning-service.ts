import { apiGet } from "@/lib/api-client"
import type { TrackDetail, TrackSummary } from "@/features/learning/types/learning"

export function fetchTracks(): Promise<TrackSummary[]> {
  return apiGet<TrackSummary[]>("/learning/tracks")
}

export function fetchTrackDetail(trackId: string): Promise<TrackDetail> {
  return apiGet<TrackDetail>(`/learning/tracks/${trackId}`)
}
