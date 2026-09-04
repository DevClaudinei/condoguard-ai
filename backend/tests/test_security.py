"""Testes unitários do núcleo de autenticação (JWT + guard de papel).

Rodam sem banco, sem FastAPI HTTP e sem modelo de IA — só PyJWT + config.
"""

import pytest
from fastapi import HTTPException

from app.api.auth_deps import ROLE_SINDICO, UsuarioAutenticado, requer_sindico
from app.core import security
from app.core.security import (
    TokenInvalidoError,
    autenticar_gestor,
    criar_access_token,
    decodificar_token,
)


def test_token_roundtrip_preserva_sub_e_role():
    token = criar_access_token(subject="sindico", role=ROLE_SINDICO)
    payload = decodificar_token(token)
    assert payload["sub"] == "sindico"
    assert payload["role"] == ROLE_SINDICO


def test_token_expirado_e_rejeitado():
    token = criar_access_token(subject="sindico", role=ROLE_SINDICO, expires_minutes=-1)
    with pytest.raises(TokenInvalidoError):
        decodificar_token(token)


def test_token_com_assinatura_invalida_e_rejeitado():
    token = criar_access_token(subject="sindico", role=ROLE_SINDICO)
    adulterado = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(TokenInvalidoError):
        decodificar_token(adulterado)


def test_autenticar_gestor(monkeypatch):
    monkeypatch.setattr(security.settings, "admin_username", "sindico")
    monkeypatch.setattr(security.settings, "admin_password", "s3nh4-forte")
    assert autenticar_gestor("sindico", "s3nh4-forte") is True
    assert autenticar_gestor("sindico", "errada") is False
    assert autenticar_gestor("outro", "s3nh4-forte") is False


def test_login_desabilitado_sem_admin_password(monkeypatch):
    monkeypatch.setattr(security.settings, "admin_password", "")
    assert autenticar_gestor("sindico", "qualquer") is False


def test_requer_sindico_autoriza_papel_correto():
    usuario = UsuarioAutenticado(subject="sindico", role=ROLE_SINDICO)
    assert requer_sindico(usuario=usuario) is usuario


def test_requer_sindico_bloqueia_papel_incorreto():
    usuario = UsuarioAutenticado(subject="morador", role="morador")
    with pytest.raises(HTTPException) as exc:
        requer_sindico(usuario=usuario)
    assert exc.value.status_code == 403


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
