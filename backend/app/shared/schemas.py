from datetime import datetime

from pydantic import BaseModel, Field


class ResponseMetadata(BaseModel):
    request_id: str
    execution_time_ms: float


class SuccessResponse[T](BaseModel):
    success: bool = True
    message: str
    data: T
    metadata: ResponseMetadata


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    trace_id: str
    timestamp: datetime
