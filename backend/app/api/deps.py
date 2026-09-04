from typing import TYPE_CHECKING

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.repositories.chamado_repository import ChamadoRepository
from app.services.triagem_service import TriagemService

if TYPE_CHECKING:
    from app.core.classifier import TriagemEngine

# Singleton preguiçoso do motor de IA: o import do módulo classifier (Torch) é
# adiado para o primeiro request, mantendo o app importável em testes sem o modelo.
_engine_singleton: "TriagemEngine | None" = None


def get_engine() -> "TriagemEngine":
    global _engine_singleton
    if _engine_singleton is None:
        from app.core.classifier import TriagemEngine  # import tardio (carrega Torch)

        _engine_singleton = TriagemEngine()
    return _engine_singleton


def get_repository(db: Session = Depends(get_db)) -> ChamadoRepository:
    return ChamadoRepository(db)


def get_triagem_service(
    repo: ChamadoRepository = Depends(get_repository),
    engine: "TriagemEngine" = Depends(get_engine),
) -> TriagemService:
    return TriagemService(repo=repo, engine=engine, settings=settings)
