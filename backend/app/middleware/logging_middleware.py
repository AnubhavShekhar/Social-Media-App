import logging
import time
from typing import Callable
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("app.request")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request_ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start = time.perf_counter()

        logger.info(f"request_started_request_id={request_id} method={request.method} path={request.url.path}")

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.info(f"request_completed request_id={request_id} method={request.method}"
                        f" path={request.url.path} status_code={response.status_code} duration_ms={duration_ms}")
            
            response.headers["X-Request-ID"] = request_id
            return response
        
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                f"request_failed request_id={request_id} method={request.method}"
                f" path={request.url.path} duration_ms={duration_ms}"
            )
            raise

        