"""Testes unitários do TriagemService usando fakes (sem banco e sem modelo de IA).

Demonstram o ganho do desacoplamento: a regra de negócio é exercitada com um
repositório e um classificador falsos, sem FastAPI, PostgreSQL ou sentence-transformers.
"""

from types import SimpleNamespace

import pytest

from app.models.chamado import ChamadoDB
from app.schemas.chamado import ChamadoCreate, UrgenciaEnum
from app.services.triagem_service import TriagemService

VETOR_FAKE = [0.1] * 384


class FakeClassificador:
    def __init__(self, urgencia: UrgenciaEnum, score: float = 0.9):
        self._urgencia = urgencia
        self._score = score

    def classificar(self, texto: str):
        return self._urgencia, self._score, VETOR_FAKE


class FakeRepository:
    def __init__(self, similar: ChamadoDB | None = None):
        self._similar = similar
        self.salvos: list[ChamadoDB] = []

    def buscar_similar(self, *, vetor, urgencia, janela, limiar):
        return self._similar

    def salvar(self, registro: ChamadoDB) -> ChamadoDB:
        if registro.id is None:
            registro.id = "CMD-NEW001"
        self.salvos.append(registro)
        return registro

    def listar(self, *, limit=100, offset=0):
        return self.salvos


def _settings():
    return SimpleNamespace(dedup_janela_horas=4, dedup_limiar_cosseno=0.35)


def _dto():
    return ChamadoCreate(
        torre="Torre A", apartamento="102",
        titulo="Cano rompido", descricao="Vazamento grave inundando a garagem",
    )


def test_p1_inedito_deve_notificar():
    service = TriagemService(
        repo=FakeRepository(similar=None),
        engine=FakeClassificador(UrgenciaEnum.P1_CRITICO),
        settings=_settings(),
    )

    resultado = service.triar(_dto())

    assert resultado.deve_notificar is True
    assert resultado.registro.duplicado is False
    assert resultado.registro.notificado is True
    assert resultado.registro.parent_id is None
    assert resultado.mensagem_alerta is None


def test_p1_duplicado_suprime_notificacao_e_agrupa():
    pai = ChamadoDB(id="CMD-PAI001", urgencia="P1_CRITICO", parent_id=None)
    service = TriagemService(
        repo=FakeRepository(similar=pai),
        engine=FakeClassificador(UrgenciaEnum.P1_CRITICO),
        settings=_settings(),
    )

    resultado = service.triar(_dto())

    assert resultado.deve_notificar is False
    assert resultado.registro.duplicado is True
    assert resultado.registro.parent_id == "CMD-PAI001"
    assert "CMD-PAI001" in resultado.mensagem_alerta


def test_duplicado_achata_cadeia_para_a_raiz():
    filho = ChamadoDB(id="CMD-FILHO1", urgencia="P1_CRITICO", parent_id="CMD-RAIZ01")
    service = TriagemService(
        repo=FakeRepository(similar=filho),
        engine=FakeClassificador(UrgenciaEnum.P1_CRITICO),
        settings=_settings(),
    )

    resultado = service.triar(_dto())

    # Aponta para a raiz (parent_id do similar), não para o similar intermediário.
    assert resultado.registro.parent_id == "CMD-RAIZ01"


def test_p3_inedito_nao_notifica():
    service = TriagemService(
        repo=FakeRepository(similar=None),
        engine=FakeClassificador(UrgenciaEnum.P3_ROTINA, score=0.4),
        settings=_settings(),
    )

    resultado = service.triar(_dto())

    assert resultado.deve_notificar is False
    assert resultado.registro.notificado is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
