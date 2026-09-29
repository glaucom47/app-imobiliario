"""
Serviço de Autenticação, Criptografia e Emissão de Tokens JWT - Fecho (fecho.pt).

Conforme estipulado no FSD e AGENTS.md:
- Senhas protegidas exclusivamente via Bcrypt irreversível (rounds=12);
- Tokens JWT gerados com algoritmo HMAC-SHA256 (HS256) e claims obrigatórios:
  'sub' (ID do usuário), 'agencia_id' (isolamento multi-tenant) e 'role' (RBAC);
- Prevenção do wrap bug do passlib através do uso direto da API moderna do bcrypt.
"""
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional
import unicodedata
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config.config import settings
from app.models.objection import ObjectionTag
from app.models.settings import Settings
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth_schema import RegisterAgencyRequest, RegisterConsultorRequest


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


def slugify(text: str) -> str:
    """Gera um slug amigável e limpo para URLs e identificação de agências."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    cleaned = re.sub(r"[^\w\s-]", "", normalized.lower()).strip()
    return re.sub(r"[-\s]+", "-", cleaned) or "agencia"


def generate_unique_tenant_slug(db: Session, base_name: str) -> str:
    """Gera um slug único para a agência, prevenindo colisões no banco de dados."""
    base_slug = slugify(base_name)
    slug = base_slug
    counter = 1

    while db.query(Tenant).filter(Tenant.slug == slug).first():
        counter += 1
        slug = f"{base_slug}-{counter}"

    return slug


def register_agency(db: Session, data: RegisterAgencyRequest) -> User:
    """
    Regista uma nova agência imobiliária com o seu diretor responsável.
    Cria automaticamente o tenant, utilizador diretor, configurações padrão da agência
    e o catálogo inicial de tags de objeções padronizadas.
    """
    clean_email = data.email_diretor.strip().lower()

    # 1. Verifica se já existe utilizador com este e-mail
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise ValueError("Já existe um utilizador registado com este endereço de e-mail.")

    # 2. Cria o novo Tenant (Agência)
    unique_slug = generate_unique_tenant_slug(db, data.nome_agencia)
    tenant = Tenant(
        nome=data.nome_agencia.strip(),
        slug=unique_slug,
        nif=data.nif.strip() if data.nif else None,
        telefone=data.telemovel_agencia.strip() if data.telemovel_agencia else None,
        email=clean_email,
        morada=data.morada.strip() if data.morada else None,
        ativo=True,
    )
    db.add(tenant)
    db.flush()

    # 3. Cria o utilizador Diretor com senha Bcrypt (rounds=12)
    diretor = User(
        agencia_id=tenant.id,
        nome=data.nome_diretor.strip(),
        email=clean_email,
        password_hash=hash_password(data.password),
        role="diretor",
        telemovel=data.telemovel_diretor.strip() if data.telemovel_diretor else None,
        ativo=True,
    )
    db.add(diretor)
    db.flush()

    # 4. Cria as configurações padrão da agência (agency_settings)
    settings_entry = Settings(
        agencia_id=tenant.id,
        spread_referencia=0.85,
        taxa_stress=1.50,
        prazo_max_financiamento_anos=30,
        percentual_financiamento_max=85.00,
        hora_notificacao_aniversario="09:00",
    )
    db.add(settings_entry)

    # 5. Cria o catálogo inicial de tags de objeção corporativas
    default_tags = [
        ("Preço Elevado", "preco"),
        ("Área Inferior ao Esperado", "dimensao"),
        ("Ruído da Rua / Zona Movimentada", "localizacao"),
        ("Falta de Garagem / Estacionamento", "caracteristica"),
        ("Exposição Solar Fraca", "caracteristica"),
        ("Necessita de Obras Profundas", "estado"),
        ("Piso Elevado sem Elevador", "caracteristica"),
        ("Valor de Condomínio Excessivo", "preco"),
    ]
    for tag_name, categoria in default_tags:
        db.add(ObjectionTag(
            agencia_id=tenant.id,
            tag=tag_name,
            categoria=categoria,
            ativo=True,
        ))

    db.commit()
    db.refresh(diretor)
    return diretor


def register_consultor(db: Session, data: RegisterConsultorRequest) -> User:
    """
    Regista um consultor imobiliário associado a uma agência existente e ativa.
    """
    clean_email = data.email.strip().lower()

    # 1. Verifica se a agência existe e está ativa
    tenant = db.query(Tenant).filter(Tenant.id == data.agencia_id, Tenant.ativo.is_(True)).first()
    if not tenant:
        raise ValueError("A agência selecionada não foi encontrada ou encontra-se inativa.")

    # 2. Verifica se o e-mail já existe
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise ValueError("Já existe um utilizador registado com este endereço de e-mail.")

    # 3. Cria o consultor
    consultor = User(
        agencia_id=tenant.id,
        nome=data.nome.strip(),
        email=clean_email,
        password_hash=hash_password(data.password),
        role="consultor",
        telemovel=data.telemovel.strip() if data.telemovel else None,
        ativo=True,
    )
    db.add(consultor)
    db.commit()
    db.refresh(consultor)
    return consultor


def list_active_agencies(db: Session) -> List[Tenant]:
    """Retorna lista de agências ativas para seleção pública no registo de consultores."""
    return db.query(Tenant).filter(Tenant.ativo.is_(True)).order_by(Tenant.nome.asc()).all()
