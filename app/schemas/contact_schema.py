"""
Esquemas Pydantic para Contact (Esfera de Influência, Compradores e Pós-Venda).
Conforme FSD:
- Gestão de compradores e contatos pós-venda da agência.
- Alertas de aniversário de celebração da escritura às 09:00.
- Geração de mensagens dinâmicas de pós-venda para WhatsApp em 1 toque.
- Anonimização em conformidade com o RGPD ('Cliente Anonimizado').
"""
from datetime import date, datetime
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContactBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=255, description="Nome do contato ou comprador")
    telemovel: str = Field(..., min_length=6, max_length=50, description="Telemóvel do contato para WhatsApp")
    email: Optional[str] = Field(None, max_length=255, description="E-mail opcional do contato")
    tipo: str = Field(default="comprador", description="Tipo de contato: comprador, proprietario, esfera")
    data_escritura: Optional[date] = Field(None, description="Data da celebração da escritura para alertas anuais")
    notas: Optional[str] = Field(None, description="Notas de relacionamento e histórico")
    property_id: Optional[int] = Field(None, description="Imóvel associado à compra ou angariação")

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        v_clean = v.strip().lower()
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, v_clean):
            raise ValueError("Formato de e-mail inválido.")
        return v_clean

    @field_validator("telemovel")
    @classmethod
    def validate_telemovel(cls, v: str) -> str:
        clean = re.sub(r"[^\d+]", "", v)
        if len(clean) < 6:
            raise ValueError("O telemóvel deve conter pelo menos 6 dígitos numéricos.")
        return clean

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        v_lower = v.strip().lower()
        tipos_validos = ("comprador", "proprietario", "esfera")
        if v_lower not in tipos_validos:
            raise ValueError(f"Tipo inválido. Deve ser um de: {', '.join(tipos_validos)}")
        return v_lower


class ContactCreate(ContactBase):
    consultor_id: Optional[int] = Field(None, description="ID do consultor responsável (se omitido, assume o logado)")


class ContactUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=255)
    telemovel: Optional[str] = Field(None, min_length=6, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    tipo: Optional[str] = Field(None)
    data_escritura: Optional[date] = Field(None)
    notas: Optional[str] = Field(None)
    consultor_id: Optional[int] = Field(None)
    property_id: Optional[int] = Field(None)

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.strip():
            return None
        v_clean = v.strip().lower()
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, v_clean):
            raise ValueError("Formato de e-mail inválido.")
        return v_clean

    @field_validator("telemovel")
    @classmethod
    def validate_telemovel(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = re.sub(r"[^\d+]", "", v)
        if len(clean) < 6:
            raise ValueError("O telemóvel deve conter pelo menos 6 dígitos numéricos.")
        return clean

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_lower = v.strip().lower()
        tipos_validos = ("comprador", "proprietario", "esfera")
        if v_lower not in tipos_validos:
            raise ValueError(f"Tipo inválido. Deve ser um de: {', '.join(tipos_validos)}")
        return v_lower


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agencia_id: int
    consultor_id: int
    consultor_nome: Optional[str] = None
    property_id: Optional[int] = None
    property_titulo: Optional[str] = None
    nome: str
    telemovel: str
    email: Optional[str] = None
    tipo: str
    data_escritura: Optional[date] = None
    anonimizado: bool = False
    notas: Optional[str] = None
    anos_escritura: Optional[int] = Field(None, description="Número de anos desde a celebração da escritura")
    is_aniversario_hoje: bool = Field(False, description="Indica se hoje é aniversário da escritura")
    created_at: datetime
    updated_at: datetime


class ContactListResponse(BaseModel):
    total: int
    aniversariantes_hoje: int
    items: List[ContactResponse]


class ContactWhatsAppRequest(BaseModel):
    tipo_mensagem: str = Field(
        default="aniversario_escritura",
        description="Tipo de mensagem: 'aniversario_escritura', 'pos_venda_geral', 'convite_cafe', 'valorizacao_patrimonial'"
    )
    custom_texto: Optional[str] = Field(None, description="Texto personalizado opcional para substituir o template")


class ContactWhatsAppResponse(BaseModel):
    contact_id: int
    contact_nome: str
    telemovel: str
    tipo_mensagem: str
    texto: str
    whatsapp_url: str


class AnonymizeResponse(BaseModel):
    contact_id: int
    status: str
    mensagem: str
    nome: str
    anonimizado: bool
