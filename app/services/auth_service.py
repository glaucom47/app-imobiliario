"""
Serviço de Autenticação, Criptografia e Emissão de Tokens JWT - Fecho (fecho.pt).

Conforme estipulado no FSD e AGENTS.md:
- Senhas protegidas exclusivamente via Bcrypt irreversível (rounds=12);
- Tokens JWT gerados com algoritmo HMAC-SHA256 (HS256) e claims obrigatórios:
  'sub' (ID do usuário), 'agencia_id' (isolamento multi-tenant) e 'role' (RBAC);
- Prevenção do wrap bug do passlib através do uso direto da API moderna do bcrypt.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config.config import settings
from app.models.user import User


def hash_password(password: str) -> str:
    """
    Gera um hash Bcrypt seguro com fator de custo 12.
    Utiliza bcrypt nativo diretamente para compatibilidade total e segurança estrita.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha em texto puro coincide com o hash Bcrypt armazenado.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria e assina um token JWT com algoritmo HS256 e tempo de expiração.
    Claims obrigatórios contidos em data:
    - sub: ID do usuário (como string)
    - agencia_id: ID da agência
    - role: 'diretor' ou 'consultor'
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodifica e valida a assinatura e expiração do token JWT.
    Lança JWTError caso o token seja inválido, expirado ou violado.
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    return payload


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Autentica o usuário por e-mail e senha.
    Retorna o objeto User se as credenciais forem válidas e tanto o usuário
    quanto a sua agência estiverem ativos; caso contrário retorna None.
    """
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user:
        return None

    # Verifica se o usuário e a sua agência estão ativos
    if not user.ativo:
        return None

    if user.tenant and not user.tenant.ativo:
        return None

    # Verifica a senha com o hash Bcrypt
    if not verify_password(password, user.password_hash):
        return None

    return user
