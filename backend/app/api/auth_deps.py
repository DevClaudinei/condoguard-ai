"""Dependências FastAPI de autenticação/autorização baseadas em JWT."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import TokenInvalidoError, decodificar_token

_bearer = HTTPBearer(auto_error=True)

ROLE_SINDICO = "sindico"


@dataclass
class UsuarioAutenticado:
    subject: str
    role: str


def get_current_user(
    credenciais: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UsuarioAutenticado:
    try:
        payload = decodificar_token(credenciais.credentials)
    except TokenInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    role = payload.get("role")
    if not subject or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem claims obrigatórias (sub/role)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UsuarioAutenticado(subject=subject, role=role)


def requer_sindico(
    usuario: UsuarioAutenticado = Depends(get_current_user),
) -> UsuarioAutenticado:
    """Autoriza apenas o corpo diretivo (papel síndico/gestão)."""
    if usuario.role != ROLE_SINDICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito à gestão do condomínio",
        )
    return usuario
