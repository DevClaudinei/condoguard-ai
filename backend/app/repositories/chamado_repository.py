from datetime import datetime

from sqlalchemy.orm import Session

from app.models.chamado import ChamadoDB


class ChamadoRepository:
    """Encapsula o acesso a dados de chamados (pgvector + relacional).

    Isola o SQL/ORM do serviço de domínio, permitindo que a lógica de triagem
    seja testada com um repositório fake, sem banco de dados.
    """

    def __init__(self, db: Session):
        self._db = db

    def buscar_similar(
        self,
        *,
        vetor: list[float],
        urgencia: str,
        janela: datetime,
        limiar: float,
    ) -> ChamadoDB | None:
        """Retorna o chamado mais próximo dentro da janela/limiar de cosseno, ou None."""
        return (
            self._db.query(ChamadoDB)
            .filter(
                ChamadoDB.created_at >= janela,
                ChamadoDB.urgencia == urgencia,
                ChamadoDB.embedding.cosine_distance(vetor) < limiar,
            )
            .order_by(ChamadoDB.embedding.cosine_distance(vetor).asc())
            .first()
        )

    def salvar(self, registro: ChamadoDB) -> ChamadoDB:
        self._db.add(registro)
        self._db.commit()
        self._db.refresh(registro)
        return registro

    def listar(self, *, limit: int = 100, offset: int = 0) -> list[ChamadoDB]:
        return (
            self._db.query(ChamadoDB)
            .order_by(ChamadoDB.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
