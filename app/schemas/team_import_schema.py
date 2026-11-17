"""
Schemas Pydantic para importação em lote de consultores da equipa por planilha (Excel / CSV).
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TeamImportRequest(BaseModel):
    """Payload de envio do ficheiro de planilha (base64 ou texto CSV)."""
    file_base64: Optional[str] = Field(None, description="Conteúdo do ficheiro .xlsx ou .csv em base64.")
    filename: Optional[str] = Field(None, description="Nome do ficheiro original (ex.: equipa.xlsx ou consultores.csv).")
    csv_text: Optional[str] = Field(None, description="Texto puro CSV, caso seja enviado diretamente.")
    default_password: Optional[str] = Field("Fecho2026!", description="Palavra-passe padrão caso a planilha não contenha coluna de senha.")


class TeamImportRowDetail(BaseModel):
    """Detalhe do processamento de uma linha individual da planilha."""
    linha: int
    nome: str
    email: str
    telemovel: Optional[str] = None
    status: str = Field(..., description="Status: 'criado', 'ignorado_existente', 'invalido', 'limite_atingido'")
    motivo: Optional[str] = None


class TeamImportResponse(BaseModel):
    """Relatório estruturado de conclusão da importação da equipa."""
    total_lidos: int
    total_criados: int
    total_ignorados: int
    detalhes: List[TeamImportRowDetail]
    mensagem: str
