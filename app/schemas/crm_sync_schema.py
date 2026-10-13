"""
Esquemas Pydantic para Sincronização de Imóveis via Feed XML/JSON de CRMs Externos.
- eGO Real Estate, Casafari CRM, X-Feed, Kyero, etc.
- Suporta importação por URL remota ou envio direto de payload (feed_content).
- Restrito ao Diretor da Agência (RBAC: require_diretor) com isolamento multi-tenant por agencia_id.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class CRMSyncRequest(BaseModel):
    """Payload para requisição de sincronização com CRM externo."""
    feed_url: Optional[str] = Field(None, description="URL remota do Feed XML ou JSON do CRM (ex: https://crm.exemplo.com/feed.xml)")
    feed_type: Optional[str] = Field("auto", description="Tipo do feed: 'auto', 'xml', 'json', 'ego', 'casafari', 'xfeed'")
    feed_content: Optional[str] = Field(None, description="Conteúdo bruto XML/JSON do feed (útil para payloads diretos ou simulações/testes)")
    default_consultor_id: Optional[int] = Field(None, description="ID do consultor padrão para novos imóveis (se omitido, atribui ao diretor/consultor principal)")


class CRMSyncResponse(BaseModel):
    """Payload de resposta da execução de sincronização CRM."""
    sucesso: bool = Field(..., description="Indica se a sincronização foi concluída sem falhas críticas")
    agencia_id: int = Field(..., description="ID da agência associada")
    total_processados: int = Field(0, description="Total de elementos identificados no feed")
    imoveis_criados: int = Field(0, description="Quantidade de novos imóveis cadastrados")
    imoveis_atualizados: int = Field(0, description="Quantidade de imóveis existentes atualizados")
    imoveis_ignorados: int = Field(0, description="Quantidade de itens ignorados por inconsistência ou falta de dados")
    erros: List[str] = Field(default_factory=list, description="Lista de avisos ou mensagens de erro não fatais ocorridos no processo")
    mensagem: str = Field(..., description="Resumo executivo do resultado da sincronização")
