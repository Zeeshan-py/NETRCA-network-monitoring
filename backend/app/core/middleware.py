"""Small ASGI request-body bound for this JSON-only API."""
import json


class RequestBodyLimitMiddleware:
    def __init__(self, app, *, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        messages = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                body = json.dumps({"success": False, "error": {
                    "code": "REQUEST_TOO_LARGE", "message": "Request body exceeds the configured limit"
                }}).encode("utf-8")
                await send({"type": "http.response.start", "status": 413,
                            "headers": [(b"content-type", b"application/json; charset=utf-8"),
                                        (b"content-length", str(len(body)).encode("ascii")),
                                        (b"cache-control", b"no-store"),
                                        (b"x-content-type-options", b"nosniff"),
                                        (b"x-frame-options", b"DENY"),
                                        (b"referrer-policy", b"no-referrer")]})
                await send({"type": "http.response.body", "body": body})
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        index = 0

        async def replay_body():
            nonlocal index
            if index < len(messages):
                result = messages[index]
                index += 1
                return result
            return {"type": "http.disconnect"}

        await self.app(scope, replay_body, send)
