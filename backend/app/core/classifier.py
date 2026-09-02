import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
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

class TriagemEngine:
    def __init__(self):
        # O modelo usará o snapshot já baixado sem disparar novas chamadas ao Hub
        self.model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        self.centroides = {
            urgencia: np.mean(self.model.encode(exemplos), axis=0).reshape(1, -1)
            for urgencia, exemplos in BASE_CONHECIMENTO.items()
        }

    def classificar(self, texto: str) -> tuple[UrgenciaEnum, float]:
        vetor = self.model.encode([texto])
        melhor_urgencia = UrgenciaEnum.P3_ROTINA
        maior_similaridade = -1.0

        for urgencia, centroide in self.centroides.items():
            sim = float(cosine_similarity(vetor, centroide)[0][0])
            if sim > maior_similaridade:
                maior_similaridade = sim
                melhor_urgencia = urgencia

        # Regra de guarda (Guardrail determinístico)
        gatilhos = ["fogo", "gás", "fumaça", "preso", "alagamento", "curto-circuito"]
        if any(palavra in texto.lower() for palavra in gatilhos):
            return UrgenciaEnum.P1_CRITICO, max(maior_similaridade, 0.95)

        return melhor_urgencia, round(maior_similaridade, 4)
