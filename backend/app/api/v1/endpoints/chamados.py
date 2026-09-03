from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.schemas.chamado import ChamadoCreate, ChamadoResponse, UrgenciaEnum
from app.core.classifier import TriagemEngine
from app.services.notifier import enviar_alerta_urgencia
from app.config import settings
from app.database import get_db
from app.models.chamado import ChamadoDB

router = APIRouter(prefix="/chamados", tags=["Chamados"])
engine_triagem = TriagemEngine()

def get_engine():
    return engine_triagem

@router.post("/triagem", response_model=ChamadoResponse)
def submeter_chamado(
    chamado: ChamadoCreate,
    background_tasks: BackgroundTasks,
    classifier: TriagemEngine = Depends(get_engine),
    db: Session = Depends(get_db)
):
    texto = f"{chamado.titulo}. {chamado.descricao}"
    # Vetorização única: classificação e vetor de persistência no mesmo encode.
    urgencia, score, vetor = classifier.classificar(texto)

    # Janela de tempo configurável (evita número mágico hardcoded)
    janela_tempo = datetime.now(timezone.utc) - timedelta(hours=settings.dedup_janela_horas)

    # Busca no PostgreSQL usando pgvector:
    # 0.0 = idêntico | limiar configurável = semantismo correlato no mesmo contexto
    similar_existente = (
        db.query(ChamadoDB)
        .filter(
            ChamadoDB.created_at >= janela_tempo,
            ChamadoDB.urgencia == urgencia.value,
            ChamadoDB.embedding.cosine_distance(vetor) < settings.dedup_limiar_cosseno
        )
        .order_by(ChamadoDB.embedding.cosine_distance(vetor).asc())
        .first()
    )

    eh_duplicado = False
    chamado_pai_id = None
    notificado = False
    mensagem_status = None

    if similar_existente:
        print(f"[DEDUP] Incidente correlato encontrado! ID Pai: {similar_existente.id}")
    else:
        print("[DEDUP] Nenhum incidente similar recente encontrado no raio de 0.35.")

    if similar_existente:
        # Se já existe ocorrência análoga em andamento, agrupamos sem reenviar notificação
        eh_duplicado = True
        chamado_pai_id = similar_existente.parent_id or similar_existente.id
        mensagem_status = f"Ocorrência similar já reportada recentemente (Protocolo base: {chamado_pai_id}). Notificação agregada para evitar spam."
    else:
        # Chamado original: dispara o alerta ao corpo diretivo se for P1
        if urgencia == UrgenciaEnum.P1_CRITICO:
            background_tasks.add_task(enviar_alerta_urgencia, chamado, score)
            notificado = True

    # Persiste o chamado com os metadados de agrupamento
    novo_registro = ChamadoDB(
        torre=chamado.torre,
        apartamento=chamado.apartamento,
        titulo=chamado.titulo,
        descricao=chamado.descricao,
        urgencia=urgencia.value,
        score_confianca=score,
        notificado=notificado,
        duplicado=eh_duplicado,
        parent_id=chamado_pai_id,
        embedding=vetor
    )
    db.add(novo_registro)
    db.commit()
    db.refresh(novo_registro)

    return ChamadoResponse(
        chamado_id=novo_registro.id,
        torre=novo_registro.torre,
        apartamento=novo_registro.apartamento,
        titulo=novo_registro.titulo,
        descricao=novo_registro.descricao,
        urgencia=urgencia,
        score_confianca=score,
        notificado=notificado,
        duplicado=eh_duplicado,
        parent_id=chamado_pai_id,
        mensagem_alerta=mensagem_status
    )

@router.get("", response_model=list[ChamadoResponse])
def listar_chamados(db: Session = Depends(get_db)):
    registros = db.query(ChamadoDB).order_by(ChamadoDB.created_at.desc()).all()
    return [
        ChamadoResponse(
            chamado_id=c.id,
            torre=c.torre,
            apartamento=c.apartamento,
            titulo=c.titulo,
            descricao=c.descricao,
            urgencia=c.urgencia,
            score_confianca=c.score_confianca,
            notificado=c.notificado,
            duplicado=bool(c.duplicado),
            parent_id=c.parent_id
        )
        for c in registros
    ]
