"""Middleware de headers de segurança básicos (defense-in-depth)."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_HEADERS_SEGURANCA = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # HSTS só tem efeito sob HTTPS (ignorado em http local); inócuo em dev.
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for chave, valor in _HEADERS_SEGURANCA.items():
            response.headers.setdefault(chave, valor)
        return response
