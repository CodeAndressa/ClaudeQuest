from fastapi import Request

from app.middlewares.request_context import get_execution_time_ms, get_request_id
from app.shared.schemas import ResponseMetadata, SuccessResponse


def success_response[T](request: Request, message: str, data: T) -> SuccessResponse[T]:
    return SuccessResponse(
        message=message,
        data=data,
        metadata=ResponseMetadata(
            request_id=get_request_id(request),
            execution_time_ms=get_execution_time_ms(request),
        ),
    )
