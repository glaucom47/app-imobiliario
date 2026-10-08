"""
Controlador HTTP REST para o Assistente Virtual Imobiliário (IA Google Gemini) - MeuFecho (meufecho.pt).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database.connection import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai_schema import AIChatRequest, AIChatResponse
from app.services.gemini_service import GeminiService

router = APIRouter(
    prefix="/ai",
    tags=["Assistente IA"]
)


@router.post("/chat", response_model=AIChatResponse, status_code=status.HTTP_200_OK)
def chat_with_ai(
    payload: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para interação com o Assistente Virtual Imobiliário do MeuFecho.
    
    Exige utilizador autenticado e aplica isolamento multi-tenant (`agencia_id`).
    """
    response_text, is_mock = GeminiService.generate_response(
        message=payload.message,
        context=payload.context,
        agencia_id=current_user.agencia_id,
        force_mock=payload.force_mock or False
    )

    return AIChatResponse(
        response=response_text,
        is_mock=is_mock
    )
