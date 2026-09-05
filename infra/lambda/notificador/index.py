"""Consumidor SQS dos alertas P1 (AWS Lambda) — envia via WhatsApp/Twilio.

Recebe o evento publicado pelo backend (via SNS->SQS) e dispara a mensagem ao
corpo diretivo pela API do Twilio (WhatsApp), cujas credenciais vêm do Secrets
Manager. Usa apenas a stdlib (urllib) — sem dependências extras no pacote.

Segredo esperado em TWILIO_SECRET_ARN (JSON):
    {
      "account_sid": "ACxxxx…",
      "auth_token":  "xxxx…",
      "from": "whatsapp:+14155238886",   # número do Sandbox do Twilio
      "to":   "whatsapp:+55XXXXXXXXXXX"   # destino verificado no Sandbox
    }
Se o segredo estiver vazio/incompleto, o evento é apenas logado (não falha).

Relato de falhas parciais (batchItemFailures): só a mensagem com erro volta à
fila / segue para a DLQ.
"""

import base64
import json
import logging
import os
import urllib.parse
import urllib.request

import boto3  # disponível no runtime da Lambda

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_secrets = boto3.client("secretsmanager")
_twilio_cache: dict | None = None

TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def _twilio_creds() -> dict:
    global _twilio_cache
    if _twilio_cache is None:
        arn = os.environ["TWILIO_SECRET_ARN"]
        raw = _secrets.get_secret_value(SecretId=arn).get("SecretString") or "{}"
        _twilio_cache = json.loads(raw)
    return _twilio_cache


def _extrair_evento(body: str) -> dict:
    corpo = json.loads(body)
    # Envelope SNS -> SQS: o payload real está em "Message".
    if isinstance(corpo, dict) and "Message" in corpo and "TopicArn" in corpo:
        return json.loads(corpo["Message"])
    return corpo


def _wa(numero: str) -> str:
    """Garante o prefixo 'whatsapp:' exigido pela API do Twilio."""
    return numero if numero.startswith("whatsapp:") else f"whatsapp:{numero}"


def _montar_mensagem(evento: dict) -> str:
    try:
        confianca = f"{round(float(evento.get('score_confianca', 0)) * 100)}%"
    except (TypeError, ValueError):
        confianca = "n/d"
    return (
        "🚨 [CondoGuard - ALERTA P1]\n"
        f"{evento.get('titulo', 'Ocorrência crítica')}\n"
        f"Local: {evento.get('torre', '?')} - Apt {evento.get('apartamento', '?')}\n"
        f"Detalhe: {evento.get('descricao', '')}\n"
        f"Confiança da IA: {confianca}"
    )


def _enviar_alerta(evento: dict) -> None:
    creds = _twilio_creds()
    sid = creds.get("account_sid")
    token = creds.get("auth_token")
    origem = creds.get("from")
    destino = creds.get("to")

    if not all([sid, token, origem, destino]):
        # Fail-open no dev: sem Twilio configurado, apenas registra (não derruba o consumo).
        logger.warning("[ALERTA P1][SEM TWILIO] %s", json.dumps(evento, ensure_ascii=False))
        return

    payload = urllib.parse.urlencode(
        {"From": _wa(origem), "To": _wa(destino), "Body": _montar_mensagem(evento)}
    ).encode()

    req = urllib.request.Request(TWILIO_API.format(sid=sid), data=payload, method="POST")
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - URL fixa do Twilio
        logger.info("Alerta P1 enviado ao WhatsApp %s (HTTP %s)", destino, resp.status)


def handler(event: dict, context=None) -> dict:
    falhas: list[dict] = []
    for record in event.get("Records", []):
        try:
            _enviar_alerta(_extrair_evento(record["body"]))
        except Exception:  # noqa: BLE001 - registra e relança para retry/DLQ
            logger.exception("Falha ao processar messageId=%s", record.get("messageId"))
            falhas.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": falhas}
