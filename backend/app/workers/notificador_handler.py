"""Worker consumidor da fila SQS de alertas P1 (handler de AWS Lambda).

Cada record da SQS carrega o evento publicado pelo backend. Quando a SQS é
assinante de um tópico SNS, o corpo vem envelopado em {"Type":"Notification",
"Message": "<json>"}; este handler desembrulha ambos os formatos.

Configurar como target de uma event source mapping SQS -> Lambda, com DLQ na
fila para reprocessamento de falhas.
"""

import json
import logging

from app.services.notifier import enviar_alerta_para_gestores

logger = logging.getLogger(__name__)


def _extrair_evento(body: str) -> dict:
    corpo = json.loads(body)
    # Envelope SNS -> SQS: o payload real está em "Message".
    if isinstance(corpo, dict) and "Message" in corpo and "TopicArn" in corpo:
        return json.loads(corpo["Message"])
    return corpo


def handler(event: dict, context=None) -> dict:
    records = event.get("Records", [])
    processados = 0
    for record in records:
        try:
            evento = _extrair_evento(record["body"])
            enviar_alerta_para_gestores(evento)
            processados += 1
        except Exception:  # noqa: BLE001 - registra e segue; a SQS/DLQ cuida do retry
            logger.exception("Falha ao processar record da SQS")
            raise  # relança para que a mensagem retorne à fila / vá para a DLQ
    return {"processados": processados, "total": len(records)}
