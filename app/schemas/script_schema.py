"""
Esquemas Pydantic para Geração e Estruturação de Scripts de Vídeo Curto.
Conforme FSD e DESIGN:
- Geração de roteiros em 3 blocos: Gancho (Hook), 2 Destaques e Chamada para Ação (CTA).
- Objetivos comerciais: Angariação, Baixa de Preço e Open House.
- Estimativa de tempo de fala para ensaio no Teleprompter.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ScriptObjectiveEnum(str, Enum):
    ANGARIACAO = "angariacao"
    BAIXA_PRECO = "baixa_preco"
    OPEN_HOUSE = "open_house"


class ScriptObjectiveInfo(BaseModel):
    id: str
    nome: str
    descricao: str
    badge: str


class ScriptGenerateRequest(BaseModel):
    property_id: int = Field(..., description="ID do imóvel ativo na carteira da agência")
    objetivo: ScriptObjectiveEnum = Field(
        default=ScriptObjectiveEnum.ANGARIACAO,
        description="Objetivo comercial do vídeo: 'angariacao', 'baixa_preco' ou 'open_house'"
    )
    destaques_adicionais: Optional[List[str]] = Field(
        default=None,
        description="Destaques opcionais sugeridos pelo consultor para enriquecer o roteiro"
    )
    tom: Optional[str] = Field(
        default="sofisticado",
        description="Tom do roteiro: 'sofisticado', 'direto', 'dinamico' ou 'urgente'"
    )


class ScriptBlockResponse(BaseModel):
    ordem: int
    chave: str  # gancho, destaque_1, destaque_2, cta
    titulo: str
    tempo_estimado_segundos: int
    conteudo: str


class ScriptResponse(BaseModel):
    property_id: int
    property_titulo: str
    tipologia: str
    preco_formatado: str
    localizacao: str
    objetivo: ScriptObjectiveEnum
    objetivo_label: str
    
    # Os 3 blocos estruturados obrigatórios
    gancho: str
    destaque_1: str
    destaque_2: str
    cta: str
    
    # Blocos detalhados para visualização editorial
    blocos: List[ScriptBlockResponse]
    
    # Texto integral pronto para Teleprompter e cópia
    texto_completo: str
    
    # Métricas de leitura
    total_palavras: int
    tempo_estimado_segundos: int
    velocidade_wpm_referencia: int = 140
    
    criado_em: datetime
