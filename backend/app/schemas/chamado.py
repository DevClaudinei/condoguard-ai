from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class UrgenciaEnum(str, Enum):
    P1_CRITICO = "P1_CRITICO"
    P2_URGENTE = "P2_URGENTE"
    P3_ROTINA = "P3_ROTINA"

class ChamadoCreate(BaseModel):
    torre: str = Field(..., min_length=1, max_length=20)
    apartamento: str = Field(..., min_length=1, max_length=10)
    titulo: str = Field(..., min_length=3, max_length=100)
    descricao: str = Field(..., min_length=5, max_length=1000)

class ChamadoResponse(BaseModel):
    # from_attributes: permite construir a resposta direto do objeto ORM.
    # populate_by_name: aceita também construção por nome do campo (chamado_id=...).
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    chamado_id: str = Field(validation_alias="id")
    torre: str
    apartamento: str
    titulo: str
    descricao: str
    urgencia: UrgenciaEnum
    score_confianca: float
    notificado: bool
    duplicado: bool = False
    parent_id: Optional[str] = None
    mensagem_alerta: Optional[str] = None
