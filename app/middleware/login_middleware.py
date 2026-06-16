import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("crm.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs method, path, status code, and latency for every request.
    Sensitive paths (auth) are logged without body.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        logger.info(
            "%s %s → %d  (%.1fms)  ip=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request.client.host if request.client else "unknown",
        )
        return response