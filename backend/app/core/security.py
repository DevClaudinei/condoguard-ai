"""Núcleo de autenticação: emissão e validação de JWT + verificação de senha.

Implementação self-contained (HS256 com segredo compartilhado) que serve como
degrau para a produção. O ponto de troca para o Amazon Cognito é isolado:
basta substituir `decodificar_token` por uma validação de assinatura via JWKS
(chaves públicas do user pool) — o resto da aplicação não muda.
"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


class TokenInvalidoError(Exception):
    """Levantada quando o token é inválido, expirado ou malformado."""


def criar_access_token(*, subject: str, role: str, expires_minutes: int | None = None) -> str:
    agora = datetime.now(timezone.utc)
    expira = agora + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "iat": agora,
        "exp": expira,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenInvalidoError("Token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidoError("Token inválido") from exc


def autenticar_gestor(username: str, password: str) -> bool:
    """Valida as credenciais de gestão em tempo constante.

    Credenciais vêm de Settings (env). Sem admin_password configurado, o login
    fica desabilitado (retorna False), evitando um login acidentalmente aberto.
    """
    if not settings.admin_password:
        return False
    usuario_ok = secrets.compare_digest(username, settings.admin_username)
    senha_ok = secrets.compare_digest(password, settings.admin_password)
    return usuario_ok and senha_ok
