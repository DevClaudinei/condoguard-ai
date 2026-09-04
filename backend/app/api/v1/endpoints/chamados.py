from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import get_triagem_service
from app.schemas.chamado import ChamadoCreate, ChamadoResponse
from app.services.messaging import publicar_alerta_p1
from app.services.triagem_service import TriagemService

router = APIRouter(prefix="/chamados", tags=["Chamados"])


@router.post("/triagem", response_model=ChamadoResponse)
def submeter_chamado(
    chamado: ChamadoCreate,
    background_tasks: BackgroundTasks,
    service: TriagemService = Depends(get_triagem_service),
):
    resultado = service.triar(chamado)

    if resultado.deve_notificar:
        # Desacoplado: publica o evento (SNS->SQS->worker) sem bloquear a resposta.
        background_tasks.add_task(publicar_alerta_p1, resultado.registro)

    resposta = ChamadoResponse.model_validate(resultado.registro)
    resposta.mensagem_alerta = resultado.mensagem_alerta
    return resposta


@router.get("", response_model=list[ChamadoResponse])
def listar_chamados(service: TriagemService = Depends(get_triagem_service)):
    return service.listar()
