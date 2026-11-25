"""Middleware: gắn Request ID cho mọi request, đo thời gian xử lý và ghi access log.

Viết dưới dạng ASGI thuần (không dùng BaseHTTPMiddleware) để không làm hỏng
background task / contextvars và không tốn thêm chi phí.
"""

import logging
import re
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("taskhub.access")

REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time"
# Chỉ nhận request id do client gửi nếu ngắn và an toàn (chống log injection)
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(REQUEST_ID_HEADER.lower().encode(), b"").decode()
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        # Lưu vào scope: exception handler (nằm ngoài middleware này) đọc được qua request.state
        scope.setdefault("state", {})["request_id"] = request_id

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                headers[PROCESS_TIME_HEADER] = f"{(time.perf_counter() - start) * 1000:.1f}ms"
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logger.info(
                "%s %s -> %s %.1fms rid=%s",
                scope["method"],
                scope["path"],
                status_code,
                (time.perf_counter() - start) * 1000,
                request_id,
            )
