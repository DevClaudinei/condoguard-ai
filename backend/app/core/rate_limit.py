"""Configuração do rate-limiter (slowapi) compartilhada pela aplicação.

Isolado em um módulo próprio para evitar import circular entre main e endpoints.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _chave_cliente(request: Request) -> str:
    """Identifica o cliente pelo IP, respeitando X-Forwarded-For atrás de ALB/proxy.

    Usa o primeiro IP da cadeia (cliente original); cai para o peer direto quando
    não há proxy à frente (desenvolvimento local).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_chave_cliente)
