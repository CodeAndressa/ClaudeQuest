import { apiGet, apiPost } from "@/lib/api-client"
import type {
  CompleteLessonResponse,
  TrackDetail,
  TrackSummary,
} from "@/features/learning/types/learning"

export function fetchTracks(): Promise<TrackSummary[]> {
  return apiGet<TrackSummary[]>("/learning/tracks")
}

export function fetchTrackDetail(trackId: string): Promise<TrackDetail> {
  return apiGet<TrackDetail>(`/learning/tracks/${trackId}`)
}

export function completeLesson(lessonId: string): Promise<CompleteLessonResponse> {
  return apiPost<CompleteLessonResponse>(`/learning/lessons/${lessonId}/complete`)
}
