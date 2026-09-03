from pydantic_settings import BaseSettings, SettingsConfigDict

import os

# Desativa alertas de telemetria e checagens anônimas desnecessárias do HF Hub
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

class Settings(BaseSettings):
    app_env: str = "development"
    port: int = 8000
    database_url: str = "postgresql://postgres:condopassword123@localhost:5432/condoguard_db"
    whatsapp_api_url: str = ""
    whatsapp_api_key: str = ""
    sindico_phone: str = ""
    subsindico_phone: str = ""

    # Parâmetros de deduplicação semântica (evita números mágicos no fluxo de triagem).
    dedup_janela_horas: int = 4
    dedup_limiar_cosseno: float = 0.35

    # Mensageria de alertas P1 (AWS). Sem ARN, o publisher cai para log local.
    aws_region: str = "us-east-1"
    sns_topic_p1_arn: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
