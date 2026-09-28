"""
Esquemas Pydantic para Gestão de Imóveis (Properties) - Fecho (fecho.pt).
Conforme FSD:
- Isolamento multi-tenant por agencia_id;
- Estados permitidos: 'Ativo', 'Reservado', 'Vendido';
- Regiões fiscais: 'continente', 'madeira', 'acores';
- Transição para 'Vendido' exige obrigatoriamente: nome_comprador, telefone_comprador e data_escritura.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PropertyBase(BaseModel):
    """Atributos base de um imóvel."""
    titulo: str = Field(..., min_length=3, max_length=255, description="Título comercial do imóvel (ex: T3 Duplex Avenida da Liberdade)")
    descricao: Optional[str] = Field(None, description="Descrição do imóvel e pontos fortes")
    tipologia: str = Field(..., max_length=20, description="Tipologia (T0, T1, T2, T3, T4, T5, Moradia, etc.)")
    preco: Decimal = Field(..., gt=0, description="Preço de venda anunciado em euros (€)")
    morada: Optional[str] = Field(None, max_length=255, description="Endereço / Morada do imóvel")
    concelho: Optional[str] = Field(None, max_length=100, description="Concelho (ex: Lisboa, Cascais, Porto)")
    distrito: Optional[str] = Field(None, max_length=100, description="Distrito (ex: Lisboa, Faro, Porto)")
    regiao_fiscal: str = Field(default="continente", description="Região fiscal: continente, madeira ou acores")
    area_bruta: Optional[Decimal] = Field(None, gt=0, description="Área bruta em m²")
    nome_proprietario: str = Field(..., min_length=2, max_length=255, description="Nome do proprietário para feedback de visitas")
    telefone_proprietario: str = Field(..., min_length=6, max_length=50, description="Contacto telefónico / WhatsApp do proprietário")

    @field_validator("regiao_fiscal")
    @classmethod
    def validate_regiao_fiscal(cls, v: str) -> str:
        regiao = v.strip().lower()
        if regiao not in ("continente", "madeira", "acores"):
            raise ValueError("Região fiscal inválida. Deve ser 'continente', 'madeira' ou 'acores'.")
        return regiao


class PropertyCreate(PropertyBase):
    """Payload de criação de imóvel."""
    consultor_id: Optional[int] = Field(None, description="ID do consultor responsável (se omitido, assume o usuário logado)")


class PropertyUpdate(BaseModel):
    """Payload de atualização cadastral de imóvel."""
    titulo: Optional[str] = Field(None, min_length=3, max_length=255)
    descricao: Optional[str] = None
    tipologia: Optional[str] = Field(None, max_length=20)
    preco: Optional[Decimal] = Field(None, gt=0)
    morada: Optional[str] = Field(None, max_length=255)
    concelho: Optional[str] = Field(None, max_length=100)
    distrito: Optional[str] = Field(None, max_length=100)
    regiao_fiscal: Optional[str] = None
    area_bruta: Optional[Decimal] = Field(None, gt=0)
    nome_proprietario: Optional[str] = Field(None, min_length=2, max_length=255)
    telefone_proprietario: Optional[str] = Field(None, min_length=6, max_length=50)
    consultor_id: Optional[int] = None

    @field_validator("regiao_fiscal")
    @classmethod
    def validate_regiao_fiscal(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            regiao = v.strip().lower()
            if regiao not in ("continente", "madeira", "acores"):
                raise ValueError("Região fiscal inválida. Deve ser 'continente', 'madeira' ou 'acores'.")
            return regiao
        return v


class PropertyTransitionStatus(BaseModel):
    """
    Payload para transição de status na máquina de estados do imóvel.
    Estados: 'Ativo' -> 'Reservado' -> 'Vendido' (ou retorno de 'Reservado' para 'Ativo').
    Quando novo_status == 'Vendido', exige obrigatoriamente os 3 campos:
    - nome_comprador
    - telefone_comprador
    - data_escritura
    """
    novo_status: str = Field(..., description="Novo estado do imóvel: 'Ativo', 'Reservado' ou 'Vendido'")
    nome_comprador: Optional[str] = Field(None, description="Nome completo do comprador (obrigatório se Vendido)")
    telefone_comprador: Optional[str] = Field(None, description="Telemóvel do comprador (obrigatório se Vendido)")
    data_escritura: Optional[date] = Field(None, description="Data da realização da escritura (obrigatório se Vendido)")

    @field_validator("novo_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        s = v.strip().capitalize()
        if s not in ("Ativo", "Reservado", "Vendido"):
            raise ValueError("Status inválido. Estados permitidos: 'Ativo', 'Reservado', 'Vendido'.")
        return s


class PropertyResponse(BaseModel):
    """Resposta com dados detalhados do imóvel."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    agencia_id: int
    consultor_id: int
    consultor_nome: Optional[str] = None
    titulo: str
    descricao: Optional[str] = None
    tipologia: str
    preco: Decimal
    morada: Optional[str] = None
    concelho: Optional[str] = None
    distrito: Optional[str] = None
    regiao_fiscal: str
    area_bruta: Optional[Decimal] = None
    status: str
    nome_proprietario: str
    telefone_proprietario: str
    nome_comprador: Optional[str] = None
    telefone_comprador: Optional[str] = None
    data_escritura: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class PropertyListResponse(BaseModel):
    """Resposta paginada / listagem de imóveis."""
    total: int
    properties: List[PropertyResponse]
