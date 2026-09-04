from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.auth_deps import ROLE_SINDICO
from app.core.security import autenticar_gestor, criar_access_token

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest):
    if not autenticar_gestor(dados.username, dados.password):
        # Mensagem genérica: não revela se foi usuário ou senha.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = criar_access_token(subject=dados.username, role=ROLE_SINDICO)
    return TokenResponse(access_token=token)
