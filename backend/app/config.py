from pydantic_settings import BaseSettings, SettingsConfigDict

import os

# Desativa alertas de telemetria e checagens anônimas desnecessárias do HF Hub
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

class Settings(BaseSettings):
    app_env: str = "development"
    port: int = 8000
    whatsapp_api_url: str = ""
    whatsapp_api_key: str = ""
    sindico_phone: str = ""
    subsindico_phone: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
