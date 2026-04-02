"""
RFC 7807 ``application/problem+json`` error handling for FastAPI.

Register the handlers with::

    from shared.errors import ProblemError, problem_error_handler, validation_error_handler
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(ProblemError, problem_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# RFC 7807 media type
_PROBLEM_CONTENT_TYPE = "application/problem+json"


class ProblemError(Exception):
    """Raise from any endpoint to get an RFC 7807 problem+json response.

    Parameters
    ----------
    status:
        HTTP status code (e.g. 404, 422, 500).
    title:
        Short human-readable summary (e.g. "Not Found").
    detail:
        Longer explanation specific to this occurrence.
    errors:
        Optional list of sub-errors (useful for batch validation).
    headers:
        Extra HTTP headers to include in the response.
    """

    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        errors: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail
        self.errors = errors
        self.headers = headers


async def problem_error_handler(request: Request, exc: ProblemError) -> JSONResponse:
    """Convert a :class:`ProblemError` into a JSON response."""
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": exc.title,
        "status": exc.status,
        "detail": exc.detail,
        "instance": str(request.url),
    }

    if exc.errors:
        body["errors"] = exc.errors

    logger.warning(
        "ProblemError %d on %s %s: %s",
        exc.status,
        request.method,
        request.url.path,
        exc.detail,
    )

    return JSONResponse(
        status_code=exc.status,
        content=body,
        headers={**(exc.headers or {}), "Content-Type": _PROBLEM_CONTENT_TYPE},
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert FastAPI/Pydantic validation errors into problem+json."""
    errors: list[dict[str, Any]] = []
    for err in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            }
        )

    body: dict[str, Any] = {
        "type": "about:blank",
        "title": "Validation Error",
        "status": 422,
        "detail": f"{len(errors)} validation error(s) in request",
        "instance": str(request.url),
        "errors": errors,
    }

    logger.warning(
        "Validation error on %s %s: %d error(s)",
        request.method,
        request.url.path,
        len(errors),
    )

    return JSONResponse(
        status_code=422,
        content=body,
        headers={"Content-Type": _PROBLEM_CONTENT_TYPE},
    )
