from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.core.classifier import TriagemEngine
from app.database import get_db
from app.repositories.chamado_repository import ChamadoRepository
from app.services.triagem_service import TriagemService

# Singleton preguiçoso do motor de IA: o modelo (Torch) só é carregado no
# primeiro request, mantendo o import dos módulos leve e testável.
_engine_singleton: TriagemEngine | None = None


def get_engine() -> TriagemEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = TriagemEngine()
    return _engine_singleton


def get_repository(db: Session = Depends(get_db)) -> ChamadoRepository:
    return ChamadoRepository(db)


def get_triagem_service(
    repo: ChamadoRepository = Depends(get_repository),
    engine: TriagemEngine = Depends(get_engine),
) -> TriagemService:
    return TriagemService(repo=repo, engine=engine, settings=settings)
