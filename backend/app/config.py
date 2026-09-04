from pydantic_settings import BaseSettings, SettingsConfigDict

import os

# Desativa alertas de telemetria e checagens anônimas desnecessárias do HF Hub
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

class Settings(BaseSettings):
    app_env: str = "development"
    port: int = 8000
    database_url: str = "postgresql://postgres:condopassword123@localhost:5432/condoguard_db"

    # Componentes discretos do banco (12-factor): quando POSTGRES_HOST está definido
    # (ex.: segredo do RDS injetado pelo ECS), a DSN é montada a partir deles.
    postgres_host: str = ""
    postgres_port: str = "5432"
    postgres_db: str = "condoguard_db"
    postgres_user: str = "postgres"
    postgres_password: str = ""
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

    # Autenticação JWT (gestão/síndico). Em produção, trocar por Cognito (JWKS).
    jwt_secret_key: str = "dev-inseguro-troque-em-producao-min-32-bytes"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    admin_username: str = "sindico"
    admin_password: str = ""  # vazio => login desabilitado (defina no .env)

    # CORS por ambiente: lista de origens separada por vírgula (sem wildcard em prod).
    cors_origins: str = "http://localhost:4200"

    # Rate-limiting do endpoint público de triagem (formato do slowapi/limits).
    rate_limit_triagem: str = "10/minute"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """DSN efetiva: monta a partir de POSTGRES_* quando presente, senão usa DATABASE_URL."""
        if self.postgres_host:
            from urllib.parse import quote_plus
            senha = quote_plus(self.postgres_password)
            return (
                f"postgresql://{self.postgres_user}:{senha}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return self.database_url

settings = Settings()
