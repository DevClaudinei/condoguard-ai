import re
import unicodedata

import numpy as np
from sentence_transformers import SentenceTransformer
from app.schemas.chamado import UrgenciaEnum

BASE_CONHECIMENTO = {
    UrgenciaEnum.P1_CRITICO: [
        "Vazamento grave de água inundando garagens ou corredores",
        "Pessoa presa no elevador",
        "Cheiro forte de vazamento de gás",
        "Curto circuito elétrico no quadro geral soltando fumaça e faíscas",
        "Portão veicular quebrado aberto comprometendo a segurança"
    ],
    UrgenciaEnum.P2_URGENTE: [
        "Interfone da portaria parou de funcionar na torre inteira",
        "Lâmpada queimada na escadaria principal",
        "Som alto após o horário de silêncio",
        "Porta de acesso de pedestres com trinco emperrado"
    ],
    UrgenciaEnum.P3_ROTINA: [
        "Solicitação de segunda via de boleto",
        "Reserva do salão de festas ou quiosque de churrasco",
        "Agendamento de mudança para o fim de semana",
        "Dúvida cadastral no aplicativo do condomínio"
    ]
}

# Gatilhos determinísticos alinhados ao README (sem acentos: comparação normalizada).
GATILHOS = {
    "fogo", "gas", "fumaca", "preso", "alagamento",
    "vazamento", "cano", "curto", "incendio", "explosao"
}

# Piso mínimo de confiança semântica: abaixo disso a classificação vira ruído.
PISO_CONFIANCA = 0.25


def _normalizar(texto: str) -> str:
    """Remove diacríticos e força minúsculas para comparação determinística."""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


class TriagemEngine:
    def __init__(self):
        # O modelo usará o snapshot já baixado sem disparar novas chamadas ao Hub
        self.model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)

        # Centroides empilhados em uma única matriz (n_classes, 384).
        # Cada centroide é a média dos exemplos e é renormalizado para norma unitária,
        # de modo que o produto interno com o vetor da consulta = similaridade de cosseno.
        self._labels = list(BASE_CONHECIMENTO.keys())
        self._centroides = np.vstack([
            self._centroide_unitario(self.model.encode(exemplos, normalize_embeddings=True))
            for exemplos in BASE_CONHECIMENTO.values()
        ])

    @staticmethod
    def _centroide_unitario(vetores: np.ndarray) -> np.ndarray:
        centroide = vetores.mean(axis=0)
        norma = np.linalg.norm(centroide)
        return centroide / norma if norma > 0 else centroide

    def _guardrail_disparou(self, texto: str) -> bool:
        """Valida gatilhos por fronteira de palavra sobre o texto normalizado."""
        tokens = set(re.findall(r"\w+", _normalizar(texto)))
        return bool(tokens & GATILHOS)

    def classificar(self, texto: str) -> tuple[UrgenciaEnum, float, list[float]]:
        # Vetorização única: reutilizada para classificação E persistência (pgvector).
        vetor = self.model.encode(texto, normalize_embeddings=True)

        # Similaridades por produto interno (centroides já normalizados) -> (n_classes,)
        similaridades = self._centroides @ vetor
        idx = int(np.argmax(similaridades))
        melhor_urgencia = self._labels[idx]
        maior_similaridade = float(similaridades[idx])

        vetor_lista = vetor.tolist()

        # Guardrail determinístico: eleva para P1 mesmo com baixa similaridade semântica.
        if self._guardrail_disparou(texto):
            return UrgenciaEnum.P1_CRITICO, max(maior_similaridade, 0.95), vetor_lista

        # Piso de corte: sem sinal semântico confiável, cai defensivamente para rotina.
        if maior_similaridade < PISO_CONFIANCA:
            return UrgenciaEnum.P3_ROTINA, round(maior_similaridade, 4), vetor_lista

        return melhor_urgencia, round(maior_similaridade, 4), vetor_lista
