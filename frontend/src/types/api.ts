export interface ResponseMetadata {
  request_id: string
  execution_time_ms: number
}

export interface SuccessResponse<T> {
  success: true
  message: string
  data: T
  metadata: ResponseMetadata
}

export interface ErrorDetail {
  code: string
  message: string
  details: Record<string, unknown>
}

export interface ErrorResponse {
  success: false
  error: ErrorDetail
  trace_id: string
  timestamp: string
}

export type ApiResponse<T> = SuccessResponse<T> | ErrorResponse

export class ApiError extends Error {
  readonly code: string
  readonly details: Record<string, unknown>
  readonly traceId: string

  constructor(error: ErrorResponse) {
    super(error.error.message)
    this.name = "ApiError"
    this.code = error.error.code
    this.details = error.error.details
    this.traceId = error.trace_id
  }
}
