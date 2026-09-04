from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.chamados import router as chamados_router

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

# CORS liberado para comunicação local com Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chamados_router, prefix="/api/v1")

@app.get("/health", tags=["Monitoramento"])
def health_check():
    return {"status": "ok"}
