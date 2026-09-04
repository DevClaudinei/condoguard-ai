"""Consumidor SQS dos alertas P1 (AWS Lambda).

Recebe o evento publicado pelo backend (via SNS->SQS) e dispara a mensagem ao
corpo diretivo pelo provedor externo (Twilio/WhatsApp), cujas credenciais vêm
do Secrets Manager. Usa relato de falhas parciais (batchItemFailures) para que
apenas mensagens com erro voltem à fila / sigam para a DLQ.
"""

import json
import logging
import os

import boto3  # disponível no runtime da Lambda

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_secrets = boto3.client("secretsmanager")
_twilio_cache: dict | None = None


def _twilio_creds() -> dict:
    global _twilio_cache
    if _twilio_cache is None:
        arn = os.environ["TWILIO_SECRET_ARN"]
        raw = _secrets.get_secret_value(SecretId=arn).get("SecretString") or "{}"
        _twilio_cache = json.loads(raw)
    return _twilio_cache


def _extrair_evento(body: str) -> dict:
    corpo = json.loads(body)
    # Se a SQS não usar raw delivery, o payload vem no envelope SNS.
    if isinstance(corpo, dict) and "Message" in corpo and "TopicArn" in corpo:
        return json.loads(corpo["Message"])
    return corpo


def _enviar_alerta(evento: dict) -> None:
    creds = _twilio_creds()  # noqa: F841 - usado na chamada real ao provedor
    mensagem = (
        f"[ALERTA P1] {evento.get('torre')} Apt {evento.get('apartamento')} - "
        f"{evento.get('titulo')}"
    )
    # TODO: chamada real à API Twilio/WhatsApp usando `creds`.
    logger.info("Disparando alerta P1: %s", mensagem)


def handler(event: dict, context=None) -> dict:
    falhas: list[dict] = []
    for record in event.get("Records", []):
        try:
            _enviar_alerta(_extrair_evento(record["body"]))
        except Exception:
            logger.exception("Falha ao processar messageId=%s", record.get("messageId"))
            falhas.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": falhas}
