"""Request correlation middleware and logging filter.

Advanced Track D (Observability & Reliability): every request gets a
correlation id that is attached to structured log records, making it
easy to follow a single workflow action through the logs even when
multiple users are acting on the system in parallel.
"""

from __future__ import annotations

import contextvars
import logging
import uuid

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def current_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationFilter(logging.Filter):
    """Logging filter that injects the current correlation id."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        record.correlation_id = _correlation_id.get()
        return True


class RequestCorrelationMiddleware:
    """Assigns a correlation id to every request and response."""

    header = "HTTP_X_CORRELATION_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cid = request.META.get(self.header) or uuid.uuid4().hex[:12]
        token = _correlation_id.set(cid)
        try:
            response = self.get_response(request)
        finally:
            _correlation_id.reset(token)
        response["X-Correlation-ID"] = cid
        return response
