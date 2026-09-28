"""
Controller de Autenticação e Sessão - Fecho (fecho.pt).

Endpoints:
- POST /api/v1/auth/login: Login de consultor ou diretor, emissão de token JWT;
- GET  /api/v1/auth/me: Dados do usuário atualmente autenticado e agência;
- POST /api/v1/auth/refresh: Renovação de token de sessão ativa.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.config import settings
from database.connection import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth_schema import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _build_user_response(user: User) -> UserResponse:
    """Auxiliar para converter modelo User em UserResponse com nome da agência."""
    return UserResponse(
        id=user.id,
        agencia_id=user.agencia_id,
        agencia_nome=user.tenant.nome if user.tenant else None,
        nome=user.nome,
        email=user.email,
        role=user.role,
        telemovel=user.telemovel,
        ativo=user.ativo,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse, summary="Autenticação por e-mail e senha")
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica um consultor ou diretor com e-mail e senha.
    Retorna o token JWT assinado contendo os claims de tenant e permissão (RBAC).
    """
    user = authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas. Verifique o e-mail e a palavra-passe.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Claims obrigatórios do token
    token_claims = {
        "sub": str(user.id),
        "agencia_id": user.agencia_id,
        "role": user.role,
        "email": user.email,
    }

    access_token = create_access_token(data=token_claims)
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=_build_user_response(user)
    )


@router.get("/me", response_model=UserResponse, summary="Dados do usuário logado")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Retorna o perfil do usuário logado e os dados da sua agência associada.
    """
    return _build_user_response(current_user)


@router.post("/refresh", response_model=TokenResponse, summary="Renovação de token JWT")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Emite um novo token JWT com período de validade renovado para o usuário autenticado.
    """
    token_claims = {
        "sub": str(current_user.id),
        "agencia_id": current_user.agencia_id,
        "role": current_user.role,
        "email": current_user.email,
    }

    new_access_token = create_access_token(data=token_claims)
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=_build_user_response(current_user)
    )
