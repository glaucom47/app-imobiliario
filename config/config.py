"""
Configurações da aplicação Fecho (fecho.pt).

Conforme estipulado no FSD (Seção 3 e 4):
- Proibido o uso de arquivos de ambiente .env para credenciais da aplicação;
- As configurações residem em código protegido carregado internamente;
- Em produção (Render/Railway), parâmetros sensíveis são alimentados diretamente pelo painel do PaaS.
"""
import os
from typing import List


class Settings:
    PROJECT_NAME: str = "Fecho"
    DOMAIN: str = "fecho.pt"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Ambiente de execução: development | production | test
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")

    # Servidor ASGI
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))
    DEBUG: bool = os.environ.get("DEBUG", "true").lower() == "true"

    # Banco de Dados PostgreSQL
    # Default para desenvolvimento local na porta 5432
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/fecho_db"
    )

    # Autenticação e Segurança JWT
    # Segredos de produção devem ser fornecidos exclusivamente pelo painel do PaaS
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY",
        "fecho-dev-insecure-secret-key-replace-in-production-paas"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 horas

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://fecho.pt",
        "https://www.fecho.pt"
    ]

    # Diretórios do sistema
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    STATIC_DIR: str = os.path.join(BASE_DIR, "static")
    LOGS_DIR: str = os.path.join(BASE_DIR, "logs")


settings = Settings()
