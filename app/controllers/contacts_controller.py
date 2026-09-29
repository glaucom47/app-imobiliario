"""
Controller REST para Contacts (Esfera de Influência, Pós-Venda e Aniversários de Escritura).
Conforme FSD:
- Isolamento multi-tenant obrigatório por agencia_id.
- Listagem e cadastro de contatos e compradores pós-venda.
- Alertas e listagem de aniversários de celebração de escritura (notificações matinais).
- Geração de mensagens dinâmicas de pós-venda para WhatsApp em 1 clique (Deep Link).
- Endpoint de conformidade RGPD para anonimização ('Cliente Anonimizado').
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.contact_schema import (
    AnonymizeResponse,
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
    ContactWhatsAppRequest,
    ContactWhatsAppResponse,
)
from app.services.contact_service import ContactService

router = APIRouter(prefix="/contacts", tags=["Contatos & Esfera de Influência"])


@router.get("", response_model=ContactListResponse)
def list_contacts(
    q: Optional[str] = Query(None, description="Pesquisa por nome, telemóvel, e-mail ou notas"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo: comprador, proprietario, esfera"),
    apenas_aniversario_hoje: bool = Query(False, description="Exibir apenas contatos que fazem aniversário de escritura hoje"),
    consultor_id: Optional[int] = Query(None, description="Filtrar por consultor (apenas diretores)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista todos os contatos da esfera de influência da agência com enriquecimento de dados de aniversário.
    """
    items, total, aniversariantes_hoje = ContactService.list_contacts(
        db=db,
        current_user=current_user,
        query_str=q,
        tipo=tipo,
        apenas_aniversario_hoje=apenas_aniversario_hoje,
        consultor_id=consultor_id,
    )
    return ContactListResponse(
        total=total,
        aniversariantes_hoje=aniversariantes_hoje,
        items=items,
    )


@router.get("/anniversaries", response_model=ContactListResponse)
def get_anniversary_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna a lista de contatos que celebram aniversário da escritura hoje.
    Ideal para o card matinal das 09:00 e envio rápido de felicitações.
    """
    items = ContactService.get_anniversary_contacts(
        db=db,
        current_user=current_user,
    )
    return ContactListResponse(
        total=len(items),
        aniversariantes_hoje=len(items),
        items=items,
    )


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    contact_in: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cadastra manualmente um novo contato na esfera de influência ou pós-venda.
    """
    return ContactService.create_contact(
        db=db,
        contact_in=contact_in,
        current_user=current_user,
    )


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact_detail(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtém os detalhes completos de um contato específico.
    """
    contact = ContactService.get_contact_by_id(db, contact_id, current_user)
    return ContactService._enrich_contact_response(contact)


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    contact_in: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Atualiza dados cadastrais de um contato na esfera de influência.
    """
    return ContactService.update_contact(
        db=db,
        contact_id=contact_id,
        contact_in=contact_in,
        current_user=current_user,
    )


@router.post("/{contact_id}/whatsapp", response_model=ContactWhatsAppResponse)
def generate_whatsapp_message(
    contact_id: int,
    payload: ContactWhatsAppRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gera texto polido de relacionamento e Deep Link para abertura direta no WhatsApp.
    Tipos suportados: 'aniversario_escritura', 'pos_venda_geral', 'convite_cafe', 'valorizacao_patrimonial'.
    """
    return ContactService.generate_whatsapp_message(
        db=db,
        contact_id=contact_id,
        current_user=current_user,
        tipo_mensagem=payload.tipo_mensagem,
        custom_texto=payload.custom_texto,
    )


@router.post("/{contact_id}/anonymize", response_model=AnonymizeResponse)
def anonymize_contact_rgpd(
    contact_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Anonimiza os dados pessoais do contato/comprador de acordo com o RGPD (Direito ao Esquecimento).
    Substitui nome por 'Cliente Anonimizado', zera telemóvel e preserva integridade histórica.
    """
    client_ip = request.client.host if request.client else None
    return ContactService.anonymize_contact(
        db=db,
        contact_id=contact_id,
        current_user=current_user,
        client_ip=client_ip,
    )


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exclui um contato desvinculado da esfera de influência.
    Se for comprador com registro de escritura de imóvel, orienta o uso da rota de anonimização.
    """
    ContactService.delete_contact(
        db=db,
        contact_id=contact_id,
        current_user=current_user,
    )
    return None
