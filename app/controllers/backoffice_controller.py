"""
Controlador HTTP REST para Backoffice da Agência, Métricas e Exportações - Fecho (fecho.pt).

Endpoints restritos à Direção Comercial (RBAC: 'diretor'):
- KPIs de assiduidade e taxa de adesão ao feedback por voz;
- Inteligência consolidada de objeções por imóvel para renegociação de preços;
- Gestão do catálogo corporativo de tags de objeção;
- Parametrizações financeiras remotas (spreads, taxas de stress, LTV);
- Exportação de relatórios em formato aberto CSV (UTF-8 BOM).
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.connection import get_db
from app.dependencies import require_diretor
from app.models.objection import ObjectionTag, VisitObjection
from app.models.property import Property
from app.models.settings import Settings
from app.models.user import User
from app.models.visit import Visit
from app.schemas.report_schema import (
    AgencySettingsResponse,
    AgencySettingsUpdate,
    ConsultorAssiduidade,
    ConsultorCreateRequest,
    ConsultorResponse,
    ConsultorStatusUpdateRequest,
    ConsultorUpdateRequest,
    KPIsSummaryResponse,
    ObjectionAnalyticsItem,
    PropertyObjectionAnalyticsResponse,
    PropertyOptionItem,
    TagCreate,
    TagResponse,
    TagUpdate,
)
from app.services.auth_service import hash_password
from app.services.export_service import ExportService

router = APIRouter(prefix="/backoffice", tags=["Backoffice Web & Métricas"])


@router.get("/kpis", response_model=KPIsSummaryResponse)
def get_kpis_summary(
    dias: Optional[int] = Query(None, ge=1, le=365, description="Filtro opcional em dias (ex: 7, 30, 90)"),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """
    Retorna métricas consolidadas da agência e ranking de assiduidade dos consultores.
    Isolamento estrito por agencia_id e acesso exclusivo para diretores.
    """
    agencia_id = current_user.agencia_id

    # Base query de visitas da agência
    visitas_query = db.query(Visit).filter(Visit.agencia_id == agencia_id)
    if dias:
        cutoff = datetime.now(timezone.utc) - timedelta(days=dias)
        visitas_query = visitas_query.filter(Visit.data_visita >= cutoff)

    visitas = visitas_query.all()
    total_visitas = len(visitas)

    visitas_com_feedback = sum(
        1 for v in visitas
        if (v.transcricao or v.notas_estruturadas or (v.audio_duracao_segundos and v.audio_duracao_segundos > 0))
    )

    visitas_enviadas_proprietario = sum(
        1 for v in visitas if v.feedback_enviado_proprietario
    )

    taxa_adesao = round((visitas_com_feedback / total_visitas * 100), 1) if total_visitas > 0 else 0.0
    taxa_prestacao = round((visitas_enviadas_proprietario / total_visitas * 100), 1) if total_visitas > 0 else 0.0

    interesses = [v.nivel_interesse for v in visitas if v.nivel_interesse is not None]
    nivel_medio = round(sum(interesses) / len(interesses), 2) if interesses else 0.0

    # Top objeção no período
    contagem_tags = {}
    for v in visitas:
        for obj in v.objections:
            if obj.tag:
                contagem_tags[obj.tag.tag] = contagem_tags.get(obj.tag.tag, 0) + 1

    top_objecao = None
    if contagem_tags:
        top_objecao = max(contagem_tags.items(), key=lambda x: x[1])[0]

    # Assiduidade por consultor
    consultores = (
        db.query(User)
        .filter(User.agencia_id == agencia_id, User.role == "consultor")
        .order_by(User.nome.asc())
        .all()
    )

    consultores_list: List[ConsultorAssiduidade] = []
    for c in consultores:
        visitas_c = [v for v in visitas if v.consultor_id == c.id]
        total_c = len(visitas_c)
        com_feedback_c = sum(
            1 for v in visitas_c
            if (v.transcricao or v.notas_estruturadas or (v.audio_duracao_segundos and v.audio_duracao_segundos > 0))
        )
        taxa_c = round((com_feedback_c / total_c * 100), 1) if total_c > 0 else 0.0
        interesses_c = [v.nivel_interesse for v in visitas_c if v.nivel_interesse is not None]
        nivel_medio_c = round(sum(interesses_c) / len(interesses_c), 2) if interesses_c else 0.0
        ultima_visita = max([v.data_visita for v in visitas_c], default=None)

        consultores_list.append(
            ConsultorAssiduidade(
                consultor_id=c.id,
                nome=c.nome,
                email=c.email,
                total_visitas=total_c,
                visitas_com_feedback=com_feedback_c,
                taxa_adesao_percent=taxa_c,
                nivel_interesse_medio=nivel_medio_c,
                ultima_visita=ultima_visita,
            )
        )

    # Ordenar consultores por total de visitas decrescente
    consultores_list.sort(key=lambda x: x.total_visitas, reverse=True)

    return KPIsSummaryResponse(
        periodo_dias=dias,
        total_visitas=total_visitas,
        visitas_com_feedback=visitas_com_feedback,
        taxa_adesao_percent=taxa_adesao,
        visitas_enviadas_proprietario=visitas_enviadas_proprietario,
        taxa_prestacao_contas_percent=taxa_prestacao,
        nivel_interesse_medio=nivel_medio,
        top_objecao=top_objecao,
        consultores_assiduidade=consultores_list,
    )


@router.get("/objections-analytics", response_model=PropertyObjectionAnalyticsResponse)
def get_objections_analytics(
    property_id: Optional[int] = Query(None, description="ID do imóvel para consolidação específica"),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """
    Retorna a consolidação estatística de objeções levantadas durante as visitas,
    gerando argumento fundamentado para renegociação de preços com proprietários.
    """
    agencia_id = current_user.agencia_id

    # Obter lista de imóveis da agência para o seletor do front-end
    imoveis_db = (
        db.query(Property)
        .filter(Property.agencia_id == agencia_id)
        .order_by(Property.titulo.asc())
        .all()
    )

    imoveis_disponiveis = [
        PropertyOptionItem(
            id=p.id,
            titulo=p.titulo,
            referencia=f"FECHO-{p.id:04d}",
            preco=float(p.preco) if p.preco else 0.0,
            status=p.status,
            nome_proprietario=p.nome_proprietario,
            telefone_proprietario=p.telefone_proprietario,
        )
        for p in imoveis_db
    ]

    selected_property: Optional[Property] = None
    if property_id:
        selected_property = (
            db.query(Property)
            .filter(Property.id == property_id, Property.agencia_id == agencia_id)
            .first()
        )
        if not selected_property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imóvel não encontrado na carteira da agência."
            )

    # Consulta de visitas
    visitas_query = db.query(Visit).filter(Visit.agencia_id == agencia_id)
    if selected_property:
        visitas_query = visitas_query.filter(Visit.property_id == selected_property.id)

    visitas = visitas_query.all()
    total_visitas = len(visitas)

    # Contagem de objeções agrupadas
    tags_count = {}
    tags_meta = {}
    visitas_com_objecoes = set()

    for v in visitas:
        has_obj = False
        for obj in v.objections:
            if obj.tag:
                has_obj = True
                t_id = obj.tag.id
                tags_count[t_id] = tags_count.get(t_id, 0) + 1
                if t_id not in tags_meta:
                    tags_meta[t_id] = {
                        "tag": obj.tag.tag,
                        "categoria": obj.tag.categoria,
                    }
        if has_obj:
            visitas_com_objecoes.add(v.id)

    distribuicao: List[ObjectionAnalyticsItem] = []
    for t_id, count in sorted(tags_count.items(), key=lambda x: x[1], reverse=True):
        pct = round((count / total_visitas * 100), 1) if total_visitas > 0 else 0.0
        distribuicao.append(
            ObjectionAnalyticsItem(
                tag_id=t_id,
                tag=tags_meta[t_id]["tag"],
                categoria=tags_meta[t_id]["categoria"],
                total_ocorrencias=count,
                percentual_visitas=pct,
            )
        )

    # Construção da recomendação / argumento de renegociação
    if selected_property:
        prop_titulo = selected_property.titulo
        prop_preco = float(selected_property.preco) if selected_property.preco else 0.0
        prop_nome = selected_property.nome_proprietario or "Estimado(a) Proprietário(a)"
        prop_tel = selected_property.telefone_proprietario

        if not distribuicao:
            resumo = (
                f"Relatório de Mercado para {prop_titulo} ({prop_preco:,.2f} €):\n"
                f"Foram realizadas {total_visitas} visita(s). Até ao momento, não foram registradas objeções críticas "
                f"dos clientes compradores."
            )
        else:
            top_items = distribuicao[:3]
            linhas_obj = [f"• {item.tag}: apontado em {item.total_ocorrencias} visita(s) ({item.percentual_visitas}% dos visitantes)" for item in top_items]
            texto_obj = "\n".join(linhas_obj)

            resumo = (
                f"Estimado(a) {prop_nome},\n\n"
                f"Apresentamos o resumo consolidado de mercado relativo ao seu imóvel '{prop_titulo}' (listado a {prop_preco:,.2f} €):\n\n"
                f"Total de visitas acompanhadas: {total_visitas}\n"
                f"Visitas com feedback detalhado: {len(visitas_com_objecoes)}\n\n"
                f"Principais pontos levantados pelos potenciais compradores:\n"
                f"{texto_obj}\n\n"
                f"Parecer Técnico da Agência:\n"
                f"Os dados empíricos demonstram que existe atratividade pela localização e tipologia, porém as "
                f"objeções recorrentes indicam a necessidade de um ajuste de posicionamento de preço "
                f"para acelerar a decisão dos interessados qualificados e concretizar o fecho da venda."
            )
    else:
        prop_titulo = None
        prop_preco = None
        prop_nome = None
        prop_tel = None
        if not distribuicao:
            resumo = f"Agência com {total_visitas} visita(s) no total. Sem objeções acumuladas no período."
        else:
            top_obj = distribuicao[0]
            resumo = (
                f"Visão Geral da Agência: {total_visitas} visitas realizadas.\n"
                f"A objeção mais recorrente em toda a carteira é '{top_obj.tag}' ({top_obj.total_ocorrencias} ocorrências, "
                f"{top_obj.percentual_visitas}% de incidência global)."
            )

    return PropertyObjectionAnalyticsResponse(
        property_id=selected_property.id if selected_property else None,
        property_titulo=prop_titulo,
        property_preco=prop_preco,
        nome_proprietario=prop_nome,
        telefone_proprietario=prop_tel,
        total_visitas_imovel=total_visitas,
        total_visitas_com_objecoes=len(visitas_com_objecoes),
        distribuicao=distribuicao,
        resumo_renegociacao=resumo,
        imoveis_disponiveis=imoveis_disponiveis,
    )


@router.get("/tags", response_model=List[TagResponse])
def list_tags(
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """Lista todas as tags de objeção corporativas da agência."""
    return (
        db.query(ObjectionTag)
        .filter(ObjectionTag.agencia_id == current_user.agencia_id)
        .order_by(ObjectionTag.categoria.asc(), ObjectionTag.tag.asc())
        .all()
    )


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag_in: TagCreate,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """Cria uma nova tag de objeção corporativa para a agência."""
    agencia_id = current_user.agencia_id

    # Verifica duplicidade
    existing = (
        db.query(ObjectionTag)
        .filter(
            ObjectionTag.agencia_id == agencia_id,
            func.lower(ObjectionTag.tag) == tag_in.tag.strip().lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tag '{tag_in.tag.strip()}' já está cadastrada na agência.",
        )

    nova_tag = ObjectionTag(
        agencia_id=agencia_id,
        tag=tag_in.tag.strip(),
        categoria=tag_in.categoria.strip().lower(),
        ativo=tag_in.ativo,
    )
    db.add(nova_tag)
    db.commit()
    db.refresh(nova_tag)
    return nova_tag


@router.put("/tags/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    tag_in: TagUpdate,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """Atualiza dados ou status de ativação de uma tag de objeção corporativa."""
    agencia_id = current_user.agencia_id

    tag_db = (
        db.query(ObjectionTag)
        .filter(ObjectionTag.id == tag_id, ObjectionTag.agencia_id == agencia_id)
        .first()
    )
    if not tag_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag de objeção não encontrada na agência.",
        )

    if tag_in.tag is not None:
        tag_nome = tag_in.tag.strip()
        # Verificar duplicidade se mudou o nome
        if tag_nome.lower() != tag_db.tag.lower():
            dup = (
                db.query(ObjectionTag)
                .filter(
                    ObjectionTag.agencia_id == agencia_id,
                    func.lower(ObjectionTag.tag) == tag_nome.lower(),
                    ObjectionTag.id != tag_id,
                )
                .first()
            )
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Já existe outra tag com o nome '{tag_nome}'.",
                )
        tag_db.tag = tag_nome

    if tag_in.categoria is not None:
        tag_db.categoria = tag_in.categoria.strip().lower()

    if tag_in.ativo is not None:
        tag_db.ativo = tag_in.ativo

    db.commit()
    db.refresh(tag_db)
    return tag_db


@router.get("/settings", response_model=AgencySettingsResponse)
def get_agency_settings(
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """Retorna os parâmetros financeiros e operacionais padrão da agência."""
    agencia_id = current_user.agencia_id

    settings_db = (
        db.query(Settings)
        .filter(Settings.agencia_id == agencia_id)
        .first()
    )

    if not settings_db:
        # Cria parametrização padrão caso inexistente
        settings_db = Settings(
            agencia_id=agencia_id,
            spread_referencia=0.85,
            taxa_stress=1.50,
            prazo_max_financiamento_anos=30,
            percentual_financiamento_max=85.00,
            hora_notificacao_aniversario="09:00",
        )
        db.add(settings_db)
        db.commit()
        db.refresh(settings_db)

    return AgencySettingsResponse(
        agencia_id=settings_db.agencia_id,
        spread_referencia=float(settings_db.spread_referencia),
        taxa_stress=float(settings_db.taxa_stress),
        prazo_max_financiamento_anos=int(settings_db.prazo_max_financiamento_anos),
        percentual_financiamento_max=float(settings_db.percentual_financiamento_max),
        hora_notificacao_aniversario=settings_db.hora_notificacao_aniversario,
        updated_at=settings_db.updated_at,
    )


@router.put("/settings", response_model=AgencySettingsResponse)
def update_agency_settings(
    settings_in: AgencySettingsUpdate,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """Atualiza parâmetros financeiros e operacionais da agência."""
    agencia_id = current_user.agencia_id

    settings_db = (
        db.query(Settings)
        .filter(Settings.agencia_id == agencia_id)
        .first()
    )

    if not settings_db:
        settings_db = Settings(agencia_id=agencia_id)
        db.add(settings_db)

    if settings_in.spread_referencia is not None:
        settings_db.spread_referencia = settings_in.spread_referencia
    if settings_in.taxa_stress is not None:
        settings_db.taxa_stress = settings_in.taxa_stress
    if settings_in.prazo_max_financiamento_anos is not None:
        settings_db.prazo_max_financiamento_anos = settings_in.prazo_max_financiamento_anos
    if settings_in.percentual_financiamento_max is not None:
        settings_db.percentual_financiamento_max = settings_in.percentual_financiamento_max
    if settings_in.hora_notificacao_aniversario is not None:
        settings_db.hora_notificacao_aniversario = settings_in.hora_notificacao_aniversario

    db.commit()
    db.refresh(settings_db)

    return AgencySettingsResponse(
        agencia_id=settings_db.agencia_id,
        spread_referencia=float(settings_db.spread_referencia),
        taxa_stress=float(settings_db.taxa_stress),
        prazo_max_financiamento_anos=int(settings_db.prazo_max_financiamento_anos),
        percentual_financiamento_max=float(settings_db.percentual_financiamento_max),
        hora_notificacao_aniversario=settings_db.hora_notificacao_aniversario,
        updated_at=settings_db.updated_at,
    )


@router.get("/export/csv")
def export_csv_report(
    tipo: str = Query(..., pattern="^(visitas|imoveis|objecoes|contactos)$", description="Tipo de relatório"),
    property_id: Optional[int] = Query(None, description="Filtro opcional para relatório de objeções"),
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """
    Exportação de relatórios abertos em formato CSV com UTF-8 BOM e delimitador ';'.
    Compatível diretamente com Excel e Numbers em português.
    """
    agencia_id = current_user.agencia_id
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if tipo == "visitas":
        content = ExportService.export_visitas_csv(db=db, agencia_id=agencia_id)
        filename = f"fecho_visitas_{now_str}.csv"
    elif tipo == "imoveis":
        content = ExportService.export_imoveis_csv(db=db, agencia_id=agencia_id)
        filename = f"fecho_imoveis_{now_str}.csv"
    elif tipo == "objecoes":
        content = ExportService.export_objecoes_csv(db=db, agencia_id=agencia_id, property_id=property_id)
        filename = f"fecho_objecoes_{now_str}.csv"
    elif tipo == "contactos":
        content = ExportService.export_contactos_csv(db=db, agencia_id=agencia_id)
        filename = f"fecho_esfera_influencia_{now_str}.csv"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de relatório inválido.",
        )

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


# =====================================================================
# GESTÃO DE CONSULTORES PELA DIREÇÃO (RBAC E MULTI-TENANT ESTRITO)
# =====================================================================

@router.get("/consultores", response_model=List[ConsultorResponse])
def list_consultores(
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """
    Lista todos os consultores associados à agência do diretor autenticado.
    Garante isolamento multi-tenant estrito por agencia_id e restrição RBAC.
    """
    consultores = (
        db.query(User)
        .filter(
            User.agencia_id == current_user.agencia_id,
            User.role == "consultor",
        )
        .order_by(User.nome.asc())
        .all()
    )
    return consultores


@router.post("/consultores", response_model=ConsultorResponse, status_code=status.HTTP_201_CREATED)
def create_consultor(
    consultor_in: ConsultorCreateRequest,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """
    Cria um novo consultor na agência do diretor autenticado.
    Injeta automaticamente o agencia_id do diretor logado e gera senha com Bcrypt rounds=12.
    """
    clean_email = consultor_in.email.strip().lower()

    # Verifica se já existe utilizador com este e-mail
    existing = db.query(User).filter(func.lower(User.email) == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um utilizador registado com este endereço de e-mail.",
        )

    novo_consultor = User(
        agencia_id=current_user.agencia_id,
        nome=consultor_in.nome.strip(),
        email=clean_email,
        password_hash=hash_password(consultor_in.password),
        role="consultor",
        telemovel=consultor_in.telemovel.strip() if consultor_in.telemovel else None,
        ativo=True,
    )
    db.add(novo_consultor)
    db.commit()
    db.refresh(novo_consultor)
    return novo_consultor


@router.patch("/consultores/{consultor_id}/status", response_model=ConsultorResponse)
def update_consultor_status(
    consultor_id: int,
    status_in: ConsultorStatusUpdateRequest,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """
    Ativa ou desativa o acesso de um consultor da agência.
    Isolamento multi-tenant estrito: impede alteração de consultores de outras agências (HTTP 404).
    """
    consultor = (
        db.query(User)
        .filter(
            User.id == consultor_id,
            User.agencia_id == current_user.agencia_id,
            User.role == "consultor",
        )
        .first()
    )

    if not consultor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultor não encontrado na sua agência.",
        )

    if consultor.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido alterar o status da própria conta da direção.",
        )

    consultor.ativo = status_in.ativo
    db.commit()
    db.refresh(consultor)
    return consultor


@router.put("/consultores/{consultor_id}", response_model=ConsultorResponse)
def update_consultor(
    consultor_id: int,
    consultor_in: ConsultorUpdateRequest,
    current_user: User = Depends(require_diretor),
    db: Session = Depends(get_db),
):
    """
    Atualiza dados cadastrais de um consultor da agência (Nome, Telemóvel e opcionalmente Palavra-passe).
    """
    consultor = (
        db.query(User)
        .filter(
            User.id == consultor_id,
            User.agencia_id == current_user.agencia_id,
            User.role == "consultor",
        )
        .first()
    )

    if not consultor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultor não encontrado na sua agência.",
        )

    if consultor_in.nome is not None:
        consultor.nome = consultor_in.nome.strip()

    if consultor_in.telemovel is not None:
        consultor.telemovel = consultor_in.telemovel.strip() if consultor_in.telemovel.strip() else None

    if consultor_in.password:
        consultor.password_hash = hash_password(consultor_in.password)

    db.commit()
    db.refresh(consultor)
    return consultor

