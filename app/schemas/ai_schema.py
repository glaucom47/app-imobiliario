"""
Esquemas Pydantic para a Integração com o Assistente de IA Google Gemini - MeuFecho (meufecho.pt).
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    """Esquema de requisição para interação com o Assistente Virtual de IA."""
    message: str = Field(..., min_length=1, description="Mensagem ou instrução do utilizador para a IA.")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Contexto opcional do imóvel, visita ou negociação.")
    force_mock: Optional[bool] = Field(default=False, description="Força a resposta via simulador local (Mock).")


class AIChatResponse(BaseModel):
    """Esquema de resposta do Assistente Virtual de IA."""
    response: str = Field(..., description="Texto da resposta gerada pela IA ou pelo simulador.")
    is_mock: bool = Field(..., description="Indica se a resposta foi gerada pelo modo Mock/Simulador.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Data e hora da resposta.")

    model_config = {
        "from_attributes": True
    }
