from app.config import settings
from app.schemas.chamado import ChamadoCreate

def enviar_alerta_urgencia(chamado: ChamadoCreate, score: float):
    # Simula chamada à API de mensagens utilizando as configs protegidas
    mensagem = (
        f"[ALERTA CRÍTICO CONDOMÍNIO]\n"
        f"Local: {chamado.torre} - Apt {chamado.apartamento}\n"
        f"Ocorrência: {chamado.titulo}\n"
        f"Detalhe: {chamado.descricao}\n"
        f"Confiança: {round(score * 100, 1)}%"
    )
    print(f">> Disparando webhook para {settings.whatsapp_api_url}")
    print(f">> Destinatários: {settings.sindico_phone}, {settings.subsindico_phone}")
    print(f">> Conteúdo:\n{mensagem}")
