from fastapi.responses import JSONResponse

from app.schemas.api import ErrorResponse


def error_response(
    message: str,
    status_code: int = 500,
    error_code: str = "internal_error",
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error_code=error_code,
            message=message,
        ).model_dump(),
    )
