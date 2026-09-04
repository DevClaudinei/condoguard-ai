from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.endpoints.chamados import router as chamados_router
from app.api.v1.endpoints.auth import router as auth_router
from app.config import settings
from app.core.middleware import SecurityHeadersMiddleware
from app.core.rate_limit import limiter

from sqlalchemy import text
from app.database import Base, engine
import app.models.chamado  # Garante registro da model

# Ativa extensão pgvector se não existir e cria as tabelas
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

Base.metadata.create_all(bind=engine)

# Índices de suporte à triagem, aplicados de forma idempotente na inicialização.
# - HNSW: acelera a busca por vizinho mais próximo (ORDER BY <=> ... LIMIT) na dedup.
# - B-Tree composto: pré-filtra a janela temporal por balde de urgência.
with engine.connect() as conn:
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS idx_chamados_embedding_hnsw "
        "ON chamados USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS idx_chamados_urgencia_created "
        "ON chamados (urgencia, created_at DESC)"
    ))
    conn.commit()

app = FastAPI(
    title="CondoGuard API",
    version="1.0.0",
    description="API de Triagem Inteligente de Chamados Condominiais"
)

# Rate-limiting (slowapi): registra o limiter, o handler de 429 e o middleware.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Headers de segurança básicos em todas as respostas.
app.add_middleware(SecurityHeadersMiddleware)

# CORS restrito por ambiente (origens vindas de Settings; sem wildcard em prod).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(chamados_router, prefix="/api/v1")

@app.get("/health", tags=["Monitoramento"])
def health_check():
    return {"status": "ok"}
