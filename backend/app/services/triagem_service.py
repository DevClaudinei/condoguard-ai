from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.config import Settings
from app.models.chamado import ChamadoDB
from app.repositories.chamado_repository import ChamadoRepository
from app.schemas.chamado import ChamadoCreate, UrgenciaEnum


class Classificador(Protocol):
    """Contrato mínimo do motor de triagem.

    Depender do Protocol (e não da classe concreta TriagemEngine) evita importar
    numpy/torch na camada de serviço: os testes injetam um fake e rodam sem o modelo.
    """

    def classificar(self, texto: str) -> tuple[UrgenciaEnum, float, list[float]]:
        ...


@dataclass
class ResultadoTriagem:
    """Resultado de domínio da triagem, desacoplado da camada HTTP."""

    registro: ChamadoDB
    deve_notificar: bool
    mensagem_alerta: str | None


class TriagemService:
    """Orquestra a triagem: classificação -> deduplicação -> persistência.

    Recebe suas dependências por injeção (repositório, motor de IA e settings),
    o que torna a regra de negócio testável com mocks, sem FastAPI nem banco.
    """

    def __init__(self, repo: ChamadoRepository, engine: Classificador, settings: Settings):
        self._repo = repo
        self._engine = engine
        self._settings = settings

    def triar(self, dto: ChamadoCreate) -> ResultadoTriagem:
        texto = f"{dto.titulo}. {dto.descricao}"
        urgencia, score, vetor = self._engine.classificar(texto)

        janela = datetime.now(timezone.utc) - timedelta(hours=self._settings.dedup_janela_horas)
        similar = self._repo.buscar_similar(
            vetor=vetor,
            urgencia=urgencia.value,
            janela=janela,
            limiar=self._settings.dedup_limiar_cosseno,
        )

        eh_duplicado = similar is not None
        # Achata a cadeia de agrupamento: aponta sempre para o incidente-raiz.
        parent_id = (similar.parent_id or similar.id) if similar else None
        deve_notificar = (not eh_duplicado) and urgencia == UrgenciaEnum.P1_CRITICO

        registro = ChamadoDB(
            torre=dto.torre,
            apartamento=dto.apartamento,
            titulo=dto.titulo,
            descricao=dto.descricao,
            urgencia=urgencia.value,
            score_confianca=score,
            notificado=deve_notificar,
            duplicado=eh_duplicado,
            parent_id=parent_id,
            embedding=vetor,
        )
        registro = self._repo.salvar(registro)

        mensagem_alerta = None
        if eh_duplicado:
            mensagem_alerta = (
                f"Ocorrência similar já reportada recentemente (Protocolo base: {parent_id}). "
                "Notificação agregada para evitar spam."
            )

        return ResultadoTriagem(
            registro=registro,
            deve_notificar=deve_notificar,
            mensagem_alerta=mensagem_alerta,
        )

    def listar(self, *, limit: int = 100, offset: int = 0) -> list[ChamadoDB]:
        return self._repo.listar(limit=limit, offset=offset)
