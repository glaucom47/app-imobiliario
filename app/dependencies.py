"""
Dependências de Injeção e Segurança do FastAPI - Fecho (fecho.pt).

Implementa:
- get_db: Sessão isolada do banco de dados;
- get_current_user: Validação rigorosa de token JWT e extração do usuário com isolamento de tenant;
- get_current_tenant: Injeção da agência do usuário autenticado;
- require_diretor: Controle de acesso RBAC restrito ao perfil de Diretor;
- require_consultor: Controle de acesso RBAC para consultores e diretores.
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session, joinedload

from database.connection import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import decode_access_token
from app.services import billing_service

# Esquema de autorização HTTP Bearer (não bloqueia automaticamente para gerarmos mensagens claras em português)
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
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

    # Busca o usuário e a agência numa única query (evita lazy load extra de user.tenant em cada request)
    user = db.query(User).options(joinedload(User.tenant)).filter(
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

    _verificar_subscricao(request, user)

    return user


# Métodos sem efeitos colaterais e rotas sempre acessíveis (auth, faturação, exportação RGPD)
_METODOS_LEITURA = {"GET", "HEAD", "OPTIONS"}
_ROTAS_ISENTAS = ("/auth/", "/billing/")


def _verificar_subscricao(request: Request, user: User) -> None:
    """
    Modo só leitura: com trial expirado ou subscrição suspensa/cancelada, a agência
    continua a consultar os seus dados, mas qualquer escrita devolve 402.
    """
    if request.method.upper() in _METODOS_LEITURA:
        return
    path = request.url.path
    if any(seg in path for seg in _ROTAS_ISENTAS):
        return
    if not billing_service.escrita_permitida(user.tenant):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="O período de teste terminou ou a subscrição não está ativa. "
                   "Os seus dados estão disponíveis apenas para consulta até ativar a subscrição.",
        )


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
