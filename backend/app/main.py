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
