from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.api.auth_deps import UsuarioAutenticado, requer_sindico
from app.api.deps import get_triagem_service
from app.config import settings
from app.core.rate_limit import limiter
from app.schemas.chamado import ChamadoCreate, ChamadoResponse
from app.services.messaging import publicar_alerta_p1
from app.services.triagem_service import TriagemService

router = APIRouter(prefix="/chamados", tags=["Chamados"])


@router.post("/triagem", response_model=ChamadoResponse)
@limiter.limit(settings.rate_limit_triagem)
def submeter_chamado(
    request: Request,  # exigido pelo slowapi para identificar o cliente
    chamado: ChamadoCreate,
    background_tasks: BackgroundTasks,
    service: TriagemService = Depends(get_triagem_service),
):
    # Endpoint público (morador), protegido por rate-limiting contra flood/custo de IA.
    resultado = service.triar(chamado)

    if resultado.deve_notificar:
        background_tasks.add_task(publicar_alerta_p1, resultado.registro)

    resposta = ChamadoResponse.model_validate(resultado.registro)
    resposta.mensagem_alerta = resultado.mensagem_alerta
    return resposta


@router.get("", response_model=list[ChamadoResponse])
def listar_chamados(
    service: TriagemService = Depends(get_triagem_service),
    _: UsuarioAutenticado = Depends(requer_sindico),  # acesso restrito à gestão
):
    return service.listar()
