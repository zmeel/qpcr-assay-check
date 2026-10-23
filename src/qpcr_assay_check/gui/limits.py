"""A limit on the size of every request body the GUI accepts.

A per-route check comes too late for an upload: Starlette spools the whole multipart body to a
temporary file before the route sees it, and a request sent in chunks carries no Content-Length
to refuse it by (code review 2026-10-23). This counts the bytes as they arrive instead.
"""

from __future__ import annotations

from typing import Any

from .assays import MAX_BYTES

# every GUI form is small: the largest is an assay file of at most MAX_BYTES, which a URL-encoded
# YAML save can make up to three times longer
MAX_REQUEST_BYTES = 4 * MAX_BYTES

_MESSAGE = b"Request too large: the GUI accepts at most %d bytes." % MAX_REQUEST_BYTES


class _TooLarge(Exception):
    pass


class BodySizeLimit:
    """Pure ASGI middleware: answer 413 once a request body passes ``max_bytes``."""

    def __init__(self, app: Any, max_bytes: int = MAX_REQUEST_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope.get("headers") or []).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.max_bytes:
            await _refuse(send)
            return
        seen = 0
        started = False

        async def counting_receive() -> Any:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes:
                    raise _TooLarge
            return message

        async def tracking_send(message: Any) -> None:
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _TooLarge:
            if not started:
                await _refuse(send)


async def _refuse(send: Any) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        }
    )
    await send({"type": "http.response.body", "body": _MESSAGE})
