"""Camada de mensageria assíncrona para alertas P1.

O disparo de alerta é desacoplado do request via publicação de um evento.
Em produção (AWS), o publisher envia para um tópico SNS, que faz fan-out para
uma fila SQS consumida por um worker (Lambda) que aciona o WhatsApp/Twilio.
Localmente, sem ARN configurado, cai para um publisher de log — mantendo o
comportamento observável em desenvolvimento, sem dependência de AWS.

    POST /triagem ──► SNS (chamado.p1.criado) ──► SQS (+DLQ) ──► Lambda ──► Twilio
"""

import json
import logging
from abc import ABC, abstractmethod

from app.config import Settings, settings
from app.models.chamado import ChamadoDB

logger = logging.getLogger(__name__)


def montar_evento(registro: ChamadoDB) -> dict:
    """Serializa o chamado no contrato de evento publicado na mensageria."""
    return {
        "chamado_id": registro.id,
        "torre": registro.torre,
        "apartamento": registro.apartamento,
        "titulo": registro.titulo,
        "descricao": registro.descricao,
        "urgencia": registro.urgencia,
        "score_confianca": registro.score_confianca,
    }


class AlertaPublisher(ABC):
    @abstractmethod
    def publicar(self, evento: dict) -> None:
        ...


class LogAlertaPublisher(AlertaPublisher):
    """Fallback de desenvolvimento: apenas registra o evento em log."""

    def publicar(self, evento: dict) -> None:
        logger.warning("[ALERTA P1][LOCAL] %s", json.dumps(evento, ensure_ascii=False))


class SnsAlertaPublisher(AlertaPublisher):
    """Publica o evento em um tópico SNS (fan-out para SQS)."""

    def __init__(self, topic_arn: str, region: str):
        import boto3  # import tardio: só exigido quando SNS está configurado

        self._topic_arn = topic_arn
        self._client = boto3.client("sns", region_name=region)

    def publicar(self, evento: dict) -> None:
        self._client.publish(
            TopicArn=self._topic_arn,
            Message=json.dumps(evento, ensure_ascii=False),
            MessageAttributes={
                # Permite roteamento/filtro por urgência no SNS/SQS.
                "urgencia": {"DataType": "String", "StringValue": evento["urgencia"]},
            },
        )


_publisher_singleton: AlertaPublisher | None = None


def get_alerta_publisher(cfg: Settings = settings) -> AlertaPublisher:
    global _publisher_singleton
    if _publisher_singleton is None:
        if cfg.sns_topic_p1_arn:
            _publisher_singleton = SnsAlertaPublisher(cfg.sns_topic_p1_arn, cfg.aws_region)
            logger.info("AlertaPublisher: SNS (%s)", cfg.sns_topic_p1_arn)
        else:
            _publisher_singleton = LogAlertaPublisher()
            logger.info("AlertaPublisher: LOG local (SNS_TOPIC_P1_ARN não configurado)")
    return _publisher_singleton


def publicar_alerta_p1(registro: ChamadoDB) -> None:
    """Ponto de entrada usado pela BackgroundTask do endpoint."""
    try:
        get_alerta_publisher().publicar(montar_evento(registro))
    except Exception:  # noqa: BLE001 - não deixa a falha de alerta derrubar o request
        logger.exception("Falha ao publicar alerta P1 do chamado %s", registro.id)
