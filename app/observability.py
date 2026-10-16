"""Structured JSON logs + request ids (course L11: observability the agent can read).

Every request produces one JSON line on stdout:
  {"ts": ..., "level": "INFO", "event": "request", "request_id": "...", "method": "GET",
   "path": "/api/v1/projects", "status": 200, "duration_ms": 3.1}
Read them with `make logs` / `docker compose logs api`. Unhandled errors are logged with
the same request_id and the exception, so a failing smoke check can be traced to its cause.
"""

import contextvars
import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, Response

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
logger = logging.getLogger("taskhub")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "message": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    for name in ("taskhub", "uvicorn.error"):
        log = logging.getLogger(name)
        log.handlers = [handler]
        log.setLevel(level.upper())
        log.propagate = False
    # The access log is replaced by our structured request log.
    logging.getLogger("uvicorn.access").disabled = True


def install_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        except Exception:
            logger.exception("unhandled error", extra={"fields": {"event": "error"}})
            raise
        finally:
            logger.info(
                "request",
                extra={
                    "fields": {
                        "event": "request",
                        "method": request.method,
                        "path": request.url.path,
                        "query": request.url.query or None,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    }
                },
            )
            request_id_var.reset(token)
