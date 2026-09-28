"""
Dependências de Injeção e Segurança do FastAPI - Fecho (fecho.pt).

Implementa:
- get_db: Sessão isolada do banco de dados;
- get_current_user: Validação rigorosa de token JWT e extração do usuário com isolamento de tenant;
- get_current_tenant: Injeção da agência do usuário autenticado;
- require_diretor: Controle de acesso RBAC restrito ao perfil de Diretor;
- require_consultor: Controle de acesso RBAC para consultores e diretores.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from database.connection import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import decode_access_token

# Esquema de autorização HTTP Bearer (não bloqueia automaticamente para gerarmos mensagens claras em português)
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    Extrai e valida o token JWT do cabeçalho Authorization: Bearer <token>.
    Garante integridade, vigência e conformidade multi-tenant por agencia_id.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais de autenticação ausentes ou inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not auth or not auth.credentials:
        raise credentials_exception

    try:
        payload = decode_access_token(auth.credentials)
        user_id_str: str = payload.get("sub")
        agencia_id: int = payload.get("agencia_id")

        if user_id_str is None or agencia_id is None:
            raise credentials_exception

        user_id = int(user_id_str)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    # Busca o usuário filtrando obrigatoriamente por id e agencia_id para garantir isolamento
    user = db.query(User).filter(
        User.id == user_id,
        User.agencia_id == agencia_id
    ).first()

    if user is None:
        raise credentials_exception

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta de utilizador inativa.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.tenant and not user.tenant.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agência desativada no sistema.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_tenant(
    current_user: User = Depends(get_current_user)
) -> Tenant:
    """
    Retorna a entidade da agência (Tenant) do usuário autenticado.
    """
    if not current_user.tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agência associada não encontrada."
        )
    return current_user.tenant


async def require_diretor(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependência de controle de acesso RBAC: restrito a usuários com perfil 'diretor'.
    Consultores recebem HTTP 403 Forbidden.
    """
    if current_user.role != "diretor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito à Direção Comercial da agência."
        )
    return current_user


async def require_consultor(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependência de controle de acesso RBAC: acessível a consultores e diretores.
    """
    if current_user.role not in ("consultor", "diretor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado para o perfil atual."
        )
    return current_user
