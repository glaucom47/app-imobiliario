"""
Esquemas Pydantic para Autenticação, Sessão e Controle de Acesso (RBAC).
Conforme FSD (Seções 3, 5 e 8):
- Isolamento por agencia_id;
- Tipagem estática rigorosa;
- Claims obrigatórios: sub, agencia_id, role.
"""
from datetime import datetime
import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    """Payload para autenticação por credenciais."""
    email: str = Field(..., description="E-mail corporativo do usuário")
    password: str = Field(..., min_length=1, description="Senha de acesso")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        email = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Formato de e-mail inválido.")
        return email


class UserResponse(BaseModel):
    """Dados públicos do usuário autenticado."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    agencia_id: int
    agencia_nome: Optional[str] = None
    nome: str
    email: str
    role: str = Field(..., description="Perfil de acesso: 'diretor' ou 'consultor'")
    telemovel: Optional[str] = None
    ativo: bool
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Resposta de emissão de token JWT após login ou refresh."""
    access_token: str = Field(..., description="Token JWT assinado")
    token_type: str = Field(default="bearer", description="Tipo de autenticação")
    expires_in: int = Field(..., description="Tempo de validade em segundos")
    user: UserResponse = Field(..., description="Dados do usuário autenticado")


class TokenPayload(BaseModel):
    """Estrutura dos claims internos do token JWT."""
    sub: str = Field(..., description="ID do usuário")
    agencia_id: int = Field(..., description="ID da agência para isolamento multi-tenant")
    role: str = Field(..., description="Perfil de acesso ('diretor' | 'consultor')")
    email: Optional[str] = None
    exp: Optional[int] = None
