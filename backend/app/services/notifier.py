import logging

from app.config import settings

logger = logging.getLogger(__name__)


def enviar_alerta_para_gestores(evento: dict) -> None:
    """Formata e dispara o alerta ao corpo diretivo a partir do evento de triagem.

    Consumido pelo worker da fila (SQS -> Lambda). Aqui entraria a chamada real
    ao provedor de mensageria (Twilio/WhatsApp) via httpx; hoje apenas registra.
    """
    mensagem = (
        f"[ALERTA CRÍTICO CONDOMÍNIO]\n"
        f"Local: {evento['torre']} - Apt {evento['apartamento']}\n"
        f"Ocorrência: {evento['titulo']}\n"
        f"Detalhe: {evento['descricao']}\n"
        f"Confiança: {round(evento['score_confianca'] * 100, 1)}%"
    )
    logger.info("Disparando webhook para %s", settings.whatsapp_api_url)
    logger.info("Destinatários: %s, %s", settings.sindico_phone, settings.subsindico_phone)
    logger.info("Conteúdo do alerta:\n%s", mensagem)
