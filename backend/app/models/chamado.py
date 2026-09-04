import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, ForeignKey
from pgvector.sqlalchemy import Vector
from app.database import Base

class ChamadoDB(Base):
    __tablename__ = "chamados"

    id = Column(String, primary_key=True, default=lambda: f"CMD-{uuid.uuid4().hex[:6].upper()}")
    torre = Column(String(20), nullable=False)
    apartamento = Column(String(10), nullable=False)
    titulo = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=False)
    urgencia = Column(String(20), nullable=False)
    score_confianca = Column(Float, nullable=False)
    notificado = Column(Boolean, default=False)
    
    # Controle de duplicidade e agrupamento semântico
    duplicado = Column(Boolean, default=False)
    parent_id = Column(String, ForeignKey("chamados.id"), nullable=True)

    # Vetor de 384 dimensões
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
