"""Block local contribution writes on read-only mirror nodes."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from services.node_mode import is_write_allowed, node_mode


class ReadOnlyMirrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not is_write_allowed(path, request.method):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        f"Node is in {node_mode()} mode: local contribution writes are disabled. "
                        "Use federation sync/import to ingest peer proofs."
                    ),
                    "node_mode": node_mode(),
                },
            )
        return await call_next(request)
