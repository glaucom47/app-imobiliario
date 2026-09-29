"""
Controller de Autenticação e Sessão - Fecho (fecho.pt).

Endpoints:
- POST /api/v1/auth/login: Login de consultor ou diretor, emissão de token JWT;
- GET  /api/v1/auth/me: Dados do usuário atualmente autenticado e agência;
- POST /api/v1/auth/refresh: Renovação de token de sessão ativa.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.config import settings
from database.connection import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth_schema import (
    AgencyPublicResponse,
    LoginRequest,
    RegisterAgencyRequest,
    RegisterConsultorRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    list_active_agencies,
    register_agency,
    register_consultor,
)

router = APIRouter(prefix="/auth", tags=["Autenticação & Registo"])


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


@router.post("/register-agency", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Registo de nova agência e diretor")
async def register_new_agency(payload: RegisterAgencyRequest, db: Session = Depends(get_db)):
    """
    Cria uma nova agência (tenant) e o utilizador diretor responsável.
    Inicializa parametrizações da agência e catálogo corporativo padrão de tags de objeção.
    Retorna o token JWT e sessão já autenticada.
    """
    try:
        user = register_agency(db=db, data=payload)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )

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


@router.post("/register-consultor", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Registo de consultor imobiliário")
async def register_new_consultor(payload: RegisterConsultorRequest, db: Session = Depends(get_db)):
    """
    Regista um consultor associando-o à agência selecionada.
    Retorna o token JWT e dados do utilizador.
    """
    try:
        user = register_consultor(db=db, data=payload)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )

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


@router.get("/agencies", response_model=List[AgencyPublicResponse], summary="Listar agências ativas para registo de consultores")
async def get_active_agencies(db: Session = Depends(get_db)):
    """
    Retorna a listagem pública de agências ativas para que consultores
    possam selecionar a sua agência durante o registo no telemóvel.
    """
    tenants = list_active_agencies(db)
    return [
        AgencyPublicResponse(
            id=t.id,
            nome=t.nome,
            slug=t.slug,
            concelho=t.morada or "Portugal",
            morada=t.morada,
        )
        for t in tenants
    ]

