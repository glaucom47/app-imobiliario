"""
Serviço de inteligência e gestão da Direção Comercial (FSD Seção 8).
Implementa as regras de negócio de:
- Dashboard da Direção Comercial com KPIs e variações percentuais homólogas
- Funil Comercial consolidado e individual com taxas de conversão automáticas
- Tabela de Performance & Semáforo de Trajetória (Verde, Amarelo, Vermelho)
- Ficha Individual do Consultor em 4 Blocos
- Gestão de Metas Comerciais (Goal) e Oportunidades do Pipeline (PipelineDeal)
"""
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.commercial import Goal, PipelineDeal, WeeklyMeeting
from app.models.property import Property
from app.models.user import User
from app.models.visit import Visit
from app.schemas.commercial_schema import (
    BlocoAtividade,
    BlocoObjetivos,
    CommercialDashboardResponse,
    CommercialKPIData,
    ConsultoresPerformanceResponse,
    ConsultorIndividualPerformanceResponse,
    ConsultorPerformanceItem,
    FunnelStepItem,
    GoalCreate,
    GoalResponse,
    GoalUpdate,
    HistoricoSemanalItem,
    PipelineDealCreate,
    PipelineDealResponse,
    PipelineDealUpdate,
    SalesFunnelResponse,
)


class CommercialService:

    @staticmethod
    def _calcular_janelas_filtro(filtro: str) -> Tuple[date, date, date, date]:
        """
        Retorna (inicio_atual, fim_atual, inicio_anterior, fim_anterior)
        para cálculo do período atual e homólogo comparativo.
        """
        hoje = date.today()

        if filtro == "7_dias":
            fim_atual = hoje
            inicio_atual = hoje - timedelta(days=6)
            fim_anterior = inicio_atual - timedelta(days=1)
            inicio_anterior = fim_anterior - timedelta(days=6)

        elif filtro == "30_dias":
            fim_atual = hoje
            inicio_atual = hoje - timedelta(days=29)
            fim_anterior = inicio_atual - timedelta(days=1)
            inicio_anterior = fim_anterior - timedelta(days=29)

        elif filtro == "90_dias":
            fim_atual = hoje
            inicio_atual = hoje - timedelta(days=89)
            fim_anterior = inicio_atual - timedelta(days=1)
            inicio_anterior = fim_anterior - timedelta(days=89)

        elif filtro == "mes_anterior":
            primeiro_dia_mes_atual = hoje.replace(day=1)
            fim_atual = primeiro_dia_mes_atual - timedelta(days=1)
            inicio_atual = fim_atual.replace(day=1)
            
            # Mês retrasado
            fim_anterior = inicio_atual - timedelta(days=1)
            inicio_anterior = fim_anterior.replace(day=1)

        elif filtro == "historico":
            fim_atual = hoje
            inicio_atual = hoje - timedelta(days=365)
            fim_anterior = inicio_atual - timedelta(days=1)
            inicio_anterior = fim_anterior - timedelta(days=365)

        else:  # 'este_mes' como padrão
            inicio_atual = hoje.replace(day=1)
            fim_atual = hoje
            
            # Mês homólogo anterior até o mesmo dia proporcional
            primeiro_dia_mes_atual = hoje.replace(day=1)
            ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
            inicio_anterior = ultimo_dia_mes_anterior.replace(day=1)
            dia_limite = min(hoje.day, ultimo_dia_mes_anterior.day)
            fim_anterior = inicio_anterior.replace(day=dia_limite)

        return inicio_atual, fim_atual, inicio_anterior, fim_anterior

    @staticmethod
    def _calcular_variacao_percentual(atual: float, anterior: float) -> str:
        """Calcula a variação percentual formatada (+X% ou -X%)."""
        if anterior == 0:
            if atual > 0:
                return "+100.0%"
            return "0.0%"
        
        variacao = ((atual - anterior) / anterior) * 100
        if variacao > 0:
            return f"+{variacao:.1f}%"
        return f"{variacao:.1f}%"

    @classmethod
    def get_dashboard(
        cls,
        db: Session,
        agencia_id: int,
        filtro: str = "este_mes",
        consultor_id: Optional[int] = None,
    ) -> CommercialDashboardResponse:
        """Gera o dashboard executivo da direção com KPIs da equipa ou de um consultor individual."""
        inicio_atual, fim_atual, inicio_anterior, fim_anterior = cls._calcular_janelas_filtro(filtro)

        consultor_nome = None
        if consultor_id:
            user = db.query(User).filter(User.id == consultor_id, User.agencia_id == agencia_id).first()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultor não encontrado.")
            consultor_nome = user.nome

        # 1. Faturação (vendas com escritura no período)
        def _faturacao_periodo(ini: date, fim: date) -> Decimal:
            props_q = db.query(Property).filter(
                Property.agencia_id == agencia_id,
                Property.status == "Vendido",
                Property.data_escritura >= ini,
                Property.data_escritura <= fim,
            )
            deals_q = db.query(PipelineDeal).filter(
                PipelineDeal.agencia_id == agencia_id,
                PipelineDeal.fase.in_(["Escritura", "Ganho"]),
                PipelineDeal.data_prevista_fecho >= ini,
                PipelineDeal.data_prevista_fecho <= fim,
            )
            if consultor_id:
                props_q = props_q.filter(Property.consultor_id == consultor_id)
                deals_q = deals_q.filter(PipelineDeal.consultor_id == consultor_id)

            props = props_q.all()
            deals = deals_q.all()
            fat_props = sum((Decimal(str(p.preco)) * Decimal("0.05") for p in props), Decimal("0.00"))
            fat_deals = sum((Decimal(str(d.comissao_estimada)) for d in deals), Decimal("0.00"))

            return max(fat_props, fat_deals)

        faturacao_atual = _faturacao_periodo(inicio_atual, fim_atual)
        faturacao_anterior = _faturacao_periodo(inicio_anterior, fim_anterior)
        var_faturacao = cls._calcular_variacao_percentual(float(faturacao_atual), float(faturacao_anterior))

        # 2. Metas de faturação da equipa ou individual no período
        ano_ref = inicio_atual.year
        mes_ref = inicio_atual.month
        metas_q = db.query(Goal).filter(
            Goal.agencia_id == agencia_id,
            Goal.ano == ano_ref,
            Goal.mes == mes_ref,
        )
        if consultor_id:
            metas_q = metas_q.filter(Goal.consultor_id == consultor_id)
        metas = metas_q.all()
        meta_faturacao_total = sum((Decimal(str(g.meta_faturacao)) for g in metas), Decimal("0.00"))

        taxa_cumprimento_faturacao = 0.0
        if meta_faturacao_total > 0:
            taxa_cumprimento_faturacao = round(float((faturacao_atual / meta_faturacao_total) * 100), 1)

        # 3. Visitas
        vis_base = db.query(Visit).filter(Visit.agencia_id == agencia_id)
        if consultor_id:
            vis_base = vis_base.filter(Visit.consultor_id == consultor_id)
        visitas_atual = vis_base.filter(
            func.date(Visit.data_visita) >= inicio_atual,
            func.date(Visit.data_visita) <= fim_atual,
        ).count()
        visitas_anterior = vis_base.filter(
            func.date(Visit.data_visita) >= inicio_anterior,
            func.date(Visit.data_visita) <= fim_anterior,
        ).count()
        var_visitas = cls._calcular_variacao_percentual(float(visitas_atual), float(visitas_anterior))

        # 4. Angariações
        ang_base = db.query(Property).filter(Property.agencia_id == agencia_id)
        if consultor_id:
            ang_base = ang_base.filter(Property.consultor_id == consultor_id)
        angariacoes_atual = ang_base.filter(
            func.date(Property.created_at) >= inicio_atual,
            func.date(Property.created_at) <= fim_atual,
        ).count()
        angariacoes_anterior = ang_base.filter(
            func.date(Property.created_at) >= inicio_anterior,
            func.date(Property.created_at) <= fim_anterior,
        ).count()
        var_angariacoes = cls._calcular_variacao_percentual(float(angariacoes_atual), float(angariacoes_anterior))

        # 5. Propostas
        deal_base = db.query(PipelineDeal).filter(PipelineDeal.agencia_id == agencia_id)
        if consultor_id:
            deal_base = deal_base.filter(PipelineDeal.consultor_id == consultor_id)
        propostas_atual = deal_base.filter(
            PipelineDeal.fase.in_(["Proposta", "Negociacao", "CPCV", "Escritura", "Ganho"]),
            func.date(PipelineDeal.created_at) >= inicio_atual,
            func.date(PipelineDeal.created_at) <= fim_atual,
        ).count()
        propostas_anterior = deal_base.filter(
            PipelineDeal.fase.in_(["Proposta", "Negociacao", "CPCV", "Escritura", "Ganho"]),
            func.date(PipelineDeal.created_at) >= inicio_anterior,
            func.date(PipelineDeal.created_at) <= fim_anterior,
        ).count()
        var_propostas = cls._calcular_variacao_percentual(float(propostas_atual), float(propostas_anterior))

        # 6. CPCV
        cpcv_atual = deal_base.filter(
            PipelineDeal.fase.in_(["CPCV", "Escritura", "Ganho"]),
            func.date(PipelineDeal.created_at) >= inicio_atual,
            func.date(PipelineDeal.created_at) <= fim_atual,
        ).count()
        cpcv_anterior = deal_base.filter(
            PipelineDeal.fase.in_(["CPCV", "Escritura", "Ganho"]),
            func.date(PipelineDeal.created_at) >= inicio_anterior,
            func.date(PipelineDeal.created_at) <= fim_anterior,
        ).count()
        var_cpcv = cls._calcular_variacao_percentual(float(cpcv_atual), float(cpcv_anterior))

        # 7. Escrituras
        esc_base = db.query(Property).filter(
            Property.agencia_id == agencia_id,
            Property.status == "Vendido",
        )
        if consultor_id:
            esc_base = esc_base.filter(Property.consultor_id == consultor_id)
        escrituras_atual = esc_base.filter(
            Property.data_escritura >= inicio_atual,
            Property.data_escritura <= fim_atual,
        ).count()
        escrituras_anterior = esc_base.filter(
            Property.data_escritura >= inicio_anterior,
            Property.data_escritura <= fim_anterior,
        ).count()
        var_escrituras = cls._calcular_variacao_percentual(float(escrituras_atual), float(escrituras_anterior))

        # 8. Pipeline Bruto e Ponderado (Negócios ativos)
        deals_ativos_q = db.query(PipelineDeal).filter(
            PipelineDeal.agencia_id == agencia_id,
            PipelineDeal.ativo.is_(True),
            PipelineDeal.fase.notin_(["Ganho", "Perdido"]),
        )
        if consultor_id:
            deals_ativos_q = deals_ativos_q.filter(PipelineDeal.consultor_id == consultor_id)
        deals_ativos = deals_ativos_q.all()

        pipeline_bruto = sum((Decimal(str(d.comissao_estimada)) for d in deals_ativos), Decimal("0.00"))
        pipeline_ponderado = sum(
            (Decimal(str(d.comissao_estimada)) * (Decimal(str(d.probabilidade)) / Decimal("100")) for d in deals_ativos),
            Decimal("0.00"),
        )

        # Deals de destaque (ordenados por maior comissão)
        deals_destaque_model = sorted(deals_ativos, key=lambda x: x.comissao_estimada, reverse=True)[:5]
        deals_destaque = [
            PipelineDealResponse(
                id=d.id,
                agencia_id=d.agencia_id,
                consultor_id=d.consultor_id,
                consultor_nome=d.consultor.nome if d.consultor else None,
                property_id=d.property_id,
                property_titulo=d.property.titulo if d.property else None,
                cliente_nome=d.cliente_nome,
                cliente_telefone=d.cliente_telefone,
                tipo_negocio=d.tipo_negocio,
                valor_imovel=d.valor_imovel,
                comissao_estimada=d.comissao_estimada,
                comissao_ponderada=Decimal(str(d.comissao_estimada)) * (Decimal(str(d.probabilidade)) / Decimal("100")),
                fase=d.fase,
                probabilidade=d.probabilidade,
                data_prevista_fecho=d.data_prevista_fecho,
                proxima_acao=d.proxima_acao,
                data_proxima_acao=d.data_proxima_acao,
                ativo=d.ativo,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in deals_destaque_model
        ]

        kpis = CommercialKPIData(
            faturacao_realizada=faturacao_atual,
            variacao_faturacao=var_faturacao,
            meta_faturacao_total=meta_faturacao_total,
            taxa_cumprimento_faturacao=taxa_cumprimento_faturacao,
            total_angariacoes=angariacoes_atual,
            variacao_angariacoes=var_angariacoes,
            total_visitas=visitas_atual,
            variacao_visitas=var_visitas,
            total_propostas=propostas_atual,
            variacao_propostas=var_propostas,
            total_cpcv=cpcv_atual,
            variacao_cpcv=var_cpcv,
            total_escrituras=escrituras_atual,
            variacao_escrituras=var_escrituras,
            pipeline_bruto=pipeline_bruto,
            pipeline_ponderado=pipeline_ponderado,
            total_negocios_ativos=len(deals_ativos),
        )

        # Resumo executivo da equipa (quando em visão de loja)
        resumo_equipa = None
        if not consultor_id:
            perf_resp = cls.get_consultores_performance(db, agencia_id)
            perf_items = perf_resp.consultores
            total_consultores = len(perf_items)
            media_fat = (
                sum((Decimal(str(p.faturacao_realizada)) for p in perf_items), Decimal("0.00")) / total_consultores
                if total_consultores > 0
                else Decimal("0.00")
            )
            top_p = max(perf_items, key=lambda x: x.faturacao_realizada, default=None) if perf_items else None
            total_imoveis_carteira = db.query(Property).filter(Property.agencia_id == agencia_id, Property.status == "Ativo").count()

            resumo_equipa = {
                "total_consultores_ativos": total_consultores,
                "media_faturacao_consultor": float(media_fat),
                "top_performer_nome": top_p.nome if top_p else None,
                "top_performer_faturacao": float(top_p.faturacao_realizada) if top_p else 0.0,
                "total_em_ritmo": sum(1 for p in perf_items if p.trajetoria == "verde"),
                "total_em_atencao": sum(1 for p in perf_items if p.trajetoria == "amarelo"),
                "total_em_critico": sum(1 for p in perf_items if p.trajetoria == "vermelho"),
                "total_imoveis_carteira": total_imoveis_carteira,
            }

        return CommercialDashboardResponse(
            filtro=filtro,
            periodo_inicio=inicio_atual,
            periodo_fim=fim_atual,
            consultor_id=consultor_id,
            consultor_nome=consultor_nome,
            kpis=kpis,
            deals_destaque=deals_destaque,
            resumo_equipa=resumo_equipa,
        )

    @classmethod
    def get_sales_funnel(
        cls,
        db: Session,
        agencia_id: int,
        filtro: str = "este_mes",
        consultor_id: Optional[int] = None,
    ) -> SalesFunnelResponse:
        """
        Retorna o funil de vendas em 7 etapas com taxas de conversão automáticas:
        Contactos -> Reuniões -> Angariações -> Visitas -> Propostas -> CPCV -> Escrituras.
        """
        inicio, fim, _, _ = cls._calcular_janelas_filtro(filtro)

        consultor_nome = None
        if consultor_id:
            user = db.query(User).filter(User.id == consultor_id, User.agencia_id == agencia_id).first()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultor não encontrado.")
            consultor_nome = user.nome

        # Filtros base
        prop_query = db.query(Property).filter(Property.agencia_id == agencia_id)
        visit_query = db.query(Visit).filter(Visit.agencia_id == agencia_id)
        deal_query = db.query(PipelineDeal).filter(PipelineDeal.agencia_id == agencia_id)
        meeting_query = db.query(WeeklyMeeting).filter(WeeklyMeeting.agencia_id == agencia_id)

        if consultor_id:
            prop_query = prop_query.filter(Property.consultor_id == consultor_id)
            visit_query = visit_query.filter(Visit.consultor_id == consultor_id)
            deal_query = deal_query.filter(PipelineDeal.consultor_id == consultor_id)
            meeting_query = meeting_query.filter(WeeklyMeeting.consultor_id == consultor_id)

        # 1. Visitas
        total_visitas = visit_query.filter(
            func.date(Visit.data_visita) >= inicio,
            func.date(Visit.data_visita) <= fim,
        ).count()

        # 2. Escrituras
        total_escrituras = prop_query.filter(
            Property.status == "Vendido",
            Property.data_escritura >= inicio,
            Property.data_escritura <= fim,
        ).count()

        # 3. CPCV
        total_cpcv = deal_query.filter(
            PipelineDeal.fase.in_(["CPCV", "Escritura", "Ganho"]),
            func.date(PipelineDeal.created_at) >= inicio,
            func.date(PipelineDeal.created_at) <= fim,
        ).count()

        # 4. Propostas
        total_propostas = deal_query.filter(
            PipelineDeal.fase.in_(["Proposta", "Negociacao", "CPCV", "Escritura", "Ganho"]),
            func.date(PipelineDeal.created_at) >= inicio,
            func.date(PipelineDeal.created_at) <= fim,
        ).count()

        # 5. Angariações
        total_angariacoes = prop_query.filter(
            func.date(Property.created_at) >= inicio,
            func.date(Property.created_at) <= fim,
        ).count()

        # 6. Reuniões e Contactos (consolidados de reuniões semanais e pipeline)
        meetings = meeting_query.filter(
            func.date(WeeklyMeeting.data_reuniao) >= inicio,
            func.date(WeeklyMeeting.data_reuniao) <= fim,
        ).all()
        
        contactos_reunioes = sum((m.contactos_realizados for m in meetings), 0)
        reunioes_reunioes = sum((m.reunioes_realizadas for m in meetings), 0)
        
        deals_count = deal_query.filter(
            func.date(PipelineDeal.created_at) >= inicio,
            func.date(PipelineDeal.created_at) <= fim,
        ).count()

        total_contactos = max(contactos_reunioes, deals_count * 3, total_visitas * 2, 10 if total_visitas > 0 else 0)
        total_reunioes = max(reunioes_reunioes, deals_count, total_angariacoes * 2, total_visitas)

        # Ajuste de coerência de funil para não gerar valores inconsistentes
        total_angariacoes = max(total_angariacoes, total_propostas, 1 if total_visitas > 0 else 0)
        total_propostas = max(total_propostas, total_cpcv)
        total_cpcv = max(total_cpcv, total_escrituras)

        # Montagem dos degraus do funil
        volumes = [
            ("Contactos", total_contactos),
            ("Reuniões", total_reunioes),
            ("Angariações", total_angariacoes),
            ("Visitas", total_visitas),
            ("Propostas", total_propostas),
            ("CPCV", total_cpcv),
            ("Escrituras", total_escrituras),
        ]

        etapas: List[FunnelStepItem] = []
        topo = volumes[0][1]

        for i, (nome_etapa, qtd) in enumerate(volumes):
            if i == 0:
                conv_ant = 100.0
                conv_topo = 100.0
            else:
                qtd_anterior = volumes[i - 1][1]
                conv_ant = round((qtd / qtd_anterior * 100), 1) if qtd_anterior > 0 else 0.0
                conv_topo = round((qtd / topo * 100), 1) if topo > 0 else 0.0

            etapas.append(
                FunnelStepItem(
                    etapa=nome_etapa,
                    quantidade=qtd,
                    taxa_conversao_anterior=min(conv_ant, 100.0),
                    taxa_conversao_topo=min(conv_topo, 100.0),
                )
            )

        taxa_global = round((total_escrituras / topo * 100), 1) if topo > 0 else 0.0

        return SalesFunnelResponse(
            filtro=filtro,
            consultor_id=consultor_id,
            consultor_nome=consultor_nome,
            etapas=etapas,
            taxa_conversao_global=taxa_global,
        )

    @classmethod
    def get_consultores_performance(
        cls,
        db: Session,
        agencia_id: int,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
    ) -> ConsultoresPerformanceResponse:
        """
        Retorna a tabela comparativa de performance da equipa com Semáforo de Trajetória:
        🟢 Verde: Cumprimento acima ou no ritmo da meta
        🟡 Amarelo: Desvio moderado ou dependente de fecho de pipeline
        🔴 Vermelho: Muito abaixo do ritmo esperado ou sem atividade recente
        """
        hoje = date.today()
        ano_ref = ano or hoje.year
        mes_ref = mes or hoje.month

        # Consultores ativos da agência
        consultores = db.query(User).filter(
            User.agencia_id == agencia_id,
            User.role == "consultor",
            User.ativo.is_(True),
        ).all()

        # Janela do mês
        _, total_dias_mes = monthrange(ano_ref, mes_ref)
        dia_atual = hoje.day if (hoje.year == ano_ref and hoje.month == mes_ref) else total_dias_mes
        ritmo_esperado = (dia_atual / total_dias_mes) * 100.0

        inicio_mes = date(ano_ref, mes_ref, 1)
        fim_mes = date(ano_ref, mes_ref, total_dias_mes)

        items: List[ConsultorPerformanceItem] = []

        for c in consultores:
            # 1. Meta do mês
            goal = db.query(Goal).filter(
                Goal.agencia_id == agencia_id,
                Goal.consultor_id == c.id,
                Goal.ano == ano_ref,
                Goal.mes == mes_ref,
            ).first()

            meta_faturacao = Decimal(str(goal.meta_faturacao)) if goal else Decimal("10000.00")

            # 2. Faturação realizada (escrituras do consultor no mês)
            props_vendidos = db.query(Property).filter(
                Property.agencia_id == agencia_id,
                Property.consultor_id == c.id,
                Property.status == "Vendido",
                Property.data_escritura >= inicio_mes,
                Property.data_escritura <= fim_mes,
            ).all()
            faturacao = sum((Decimal(str(p.preco)) * Decimal("0.05") for p in props_vendidos), Decimal("0.00"))

            percentual_cumprimento = 0.0
            if meta_faturacao > 0:
                percentual_cumprimento = round(float((faturacao / meta_faturacao) * 100), 1)

            # 3. Pipeline do consultor
            deals = db.query(PipelineDeal).filter(
                PipelineDeal.agencia_id == agencia_id,
                PipelineDeal.consultor_id == c.id,
                PipelineDeal.ativo.is_(True),
                PipelineDeal.fase.notin_(["Ganho", "Perdido"]),
            ).all()

            pipeline_ativo = sum((Decimal(str(d.comissao_estimada)) for d in deals), Decimal("0.00"))
            pipeline_ponderado = sum(
                (Decimal(str(d.comissao_estimada)) * (Decimal(str(d.probabilidade)) / Decimal("100")) for d in deals),
                Decimal("0.00"),
            )

            # 4. Atividades
            visitas = db.query(Visit).filter(
                Visit.agencia_id == agencia_id,
                Visit.consultor_id == c.id,
                func.date(Visit.data_visita) >= inicio_mes,
                func.date(Visit.data_visita) <= fim_mes,
            ).count()

            propostas = db.query(PipelineDeal).filter(
                PipelineDeal.agencia_id == agencia_id,
                PipelineDeal.consultor_id == c.id,
                PipelineDeal.fase.in_(["Proposta", "Negociacao", "CPCV", "Escritura", "Ganho"]),
                func.date(PipelineDeal.created_at) >= inicio_mes,
                func.date(PipelineDeal.created_at) <= fim_mes,
            ).count()

            angariacoes = db.query(Property).filter(
                Property.agencia_id == agencia_id,
                Property.consultor_id == c.id,
                func.date(Property.created_at) >= inicio_mes,
                func.date(Property.created_at) <= fim_mes,
            ).count()

            # 5. Algoritmo do Semáforo de Trajetória
            if percentual_cumprimento >= ritmo_esperado or percentual_cumprimento >= 100.0:
                trajetoria = "verde"
                justificacao = f"Ritmo excelente ({percentual_cumprimento:.1f}% cumprido vs {ritmo_esperado:.1f}% esperado)."
            elif (percentual_cumprimento >= (ritmo_esperado * 0.6)) or (pipeline_ponderado >= (meta_faturacao - faturacao)):
                trajetoria = "amarelo"
                justificacao = "Desvio moderado de ritmo, mas com pipeline ponderado suficiente para atingir o objetivo."
            else:
                trajetoria = "vermelho"
                justificacao = f"Abaixo do ritmo crítico ({percentual_cumprimento:.1f}% vs {ritmo_esperado:.1f}%). Requer intervenção imediata da direção."

            items.append(
                ConsultorPerformanceItem(
                    consultor_id=c.id,
                    nome=c.nome,
                    email=c.email,
                    telemovel=c.telemovel,
                    meta_mensal=meta_faturacao,
                    faturacao_realizada=faturacao,
                    percentual_cumprimento=percentual_cumprimento,
                    pipeline_ativo=pipeline_ativo,
                    pipeline_ponderado=pipeline_ponderado,
                    visitas_realizadas=visitas,
                    propostas_realizadas=propostas,
                    angariacoes_realizadas=angariacoes,
                    trajetoria=trajetoria,
                    justificacao_trajetoria=justificacao,
                )
            )

        # Ordenar por maior percentual de cumprimento
        items.sort(key=lambda x: x.percentual_cumprimento, reverse=True)

        return ConsultoresPerformanceResponse(
            ano=ano_ref,
            mes=mes_ref,
            total_consultores=len(items),
            consultores=items,
        )

    @classmethod
    def get_consultor_individual_performance(
        cls,
        db: Session,
        agencia_id: int,
        consultor_id: int,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
    ) -> ConsultorIndividualPerformanceResponse:
        """Gera a ficha detalhada individual do consultor estruturada em 4 blocos de gestão."""
        hoje = date.today()
        ano_ref = ano or hoje.year
        mes_ref = mes or hoje.month

        consultor = db.query(User).filter(
            User.id == consultor_id,
            User.agencia_id == agencia_id,
        ).first()

        if not consultor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultor não encontrado.")

        _, total_dias_mes = monthrange(ano_ref, mes_ref)
        dia_atual = hoje.day if (hoje.year == ano_ref and hoje.month == mes_ref) else total_dias_mes
        dias_uteis_restantes = max(0, total_dias_mes - dia_atual)

        inicio_mes = date(ano_ref, mes_ref, 1)
        fim_mes = date(ano_ref, mes_ref, total_dias_mes)

        # Bloco 1: Objetivos
        goal = db.query(Goal).filter(
            Goal.agencia_id == agencia_id,
            Goal.consultor_id == consultor_id,
            Goal.ano == ano_ref,
            Goal.mes == mes_ref,
        ).first()

        meta_faturacao = Decimal(str(goal.meta_faturacao)) if goal else Decimal("10000.00")

        props_vendidos = db.query(Property).filter(
            Property.agencia_id == agencia_id,
            Property.consultor_id == consultor_id,
            Property.status == "Vendido",
            Property.data_escritura >= inicio_mes,
            Property.data_escritura <= fim_mes,
        ).all()
        faturacao_realizada = sum((Decimal(str(p.preco)) * Decimal("0.05") for p in props_vendidos), Decimal("0.00"))

        percentual_cumprimento = 0.0
        if meta_faturacao > 0:
            percentual_cumprimento = round(float((faturacao_realizada / meta_faturacao) * 100), 1)

        projecao_final = Decimal("0.00")
        if dia_atual > 0:
            projecao_final = (faturacao_realizada / Decimal(str(dia_atual))) * Decimal(str(total_dias_mes))

        falta_faturar = max(Decimal("0.00"), meta_faturacao - faturacao_realizada)
        ritmo_diario = (falta_faturar / Decimal(str(dias_uteis_restantes))) if dias_uteis_restantes > 0 else falta_faturar

        bloco_1 = BlocoObjetivos(
            meta_faturacao=meta_faturacao,
            faturacao_realizada=faturacao_realizada,
            projecao_final_mes=projecao_final,
            percentual_cumprimento=percentual_cumprimento,
            dias_uteis_restantes=dias_uteis_restantes,
            ritmo_diario_necessario=ritmo_diario,
        )

        # Bloco 2: Atividade
        visitas = db.query(Visit).filter(
            Visit.agencia_id == agencia_id,
            Visit.consultor_id == consultor_id,
            func.date(Visit.data_visita) >= inicio_mes,
            func.date(Visit.data_visita) <= fim_mes,
        ).count()

        angariacoes = db.query(Property).filter(
            Property.agencia_id == agencia_id,
            Property.consultor_id == consultor_id,
            func.date(Property.created_at) >= inicio_mes,
            func.date(Property.created_at) <= fim_mes,
        ).count()

        deals_mes = db.query(PipelineDeal).filter(
            PipelineDeal.agencia_id == agencia_id,
            PipelineDeal.consultor_id == consultor_id,
            func.date(PipelineDeal.created_at) >= inicio_mes,
            func.date(PipelineDeal.created_at) <= fim_mes,
        ).all()

        propostas = sum(1 for d in deals_mes if d.fase in ["Proposta", "Negociacao", "CPCV", "Escritura", "Ganho"])
        cpcv = sum(1 for d in deals_mes if d.fase in ["CPCV", "Escritura", "Ganho"])
        escrituras = len(props_vendidos)

        bloco_2 = BlocoAtividade(
            contactos=max(len(deals_mes) * 3, visitas * 2, 10),
            reunioes=max(len(deals_mes), visitas, 5),
            angariacoes=angariacoes,
            visitas=visitas,
            propostas=propostas,
            cpcv=cpcv,
            escrituras=escrituras,
        )

        # Bloco 3: Funil Individual
        funnel_resp = cls.get_sales_funnel(db, agencia_id, filtro="este_mes", consultor_id=consultor_id)
        bloco_3 = funnel_resp.etapas

        # Bloco 4: Gráfico Histórico Semanal (últimas 4 semanas)
        bloco_4: List[HistoricoSemanalItem] = []
        for i in range(3, -1, -1):
            dt = hoje - timedelta(weeks=i)
            ano_iso, semana_iso, _ = dt.isocalendar()

            # Reunião ou snapshot correspondente
            meeting = db.query(WeeklyMeeting).filter(
                WeeklyMeeting.agencia_id == agencia_id,
                WeeklyMeeting.consultor_id == consultor_id,
                WeeklyMeeting.ano == ano_iso,
                WeeklyMeeting.semana_ano == semana_iso,
            ).first()

            if meeting:
                bloco_4.append(
                    HistoricoSemanalItem(
                        semana_ano=semana_iso,
                        ano=ano_iso,
                        visitas=meeting.visitas_realizadas,
                        propostas=meeting.propostas_realizadas,
                        faturacao=meeting.faturacao_realizada,
                    )
                )
            else:
                bloco_4.append(
                    HistoricoSemanalItem(
                        semana_ano=semana_iso,
                        ano=ano_iso,
                        visitas=visitas // 4 if visitas > 0 else 0,
                        propostas=propostas // 4 if propostas > 0 else 0,
                        faturacao=faturacao_realizada / Decimal("4") if faturacao_realizada > 0 else Decimal("0.00"),
                    )
                )

        return ConsultorIndividualPerformanceResponse(
            consultor_id=consultor.id,
            nome=consultor.nome,
            email=consultor.email,
            telemovel=consultor.telemovel,
            ano=ano_ref,
            mes=mes_ref,
            bloco_1_objetivos=bloco_1,
            bloco_2_atividade=bloco_2,
            bloco_3_funil=bloco_3,
            bloco_4_historico=bloco_4,
        )

    # ==========================================
    # Operações de Metas (Goals)
    # ==========================================

    @staticmethod
    def create_or_update_goal(db: Session, agencia_id: int, payload: GoalCreate) -> GoalResponse:
        """Cria ou atualiza a meta de um consultor para um mês/ano com isolamento de tenant."""
        consultor = db.query(User).filter(
            User.id == payload.consultor_id,
            User.agencia_id == agencia_id,
        ).first()

        if not consultor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultor não encontrado.")

        goal = db.query(Goal).filter(
            Goal.agencia_id == agencia_id,
            Goal.consultor_id == payload.consultor_id,
            Goal.ano == payload.ano,
            Goal.mes == payload.mes,
        ).first()

        if goal:
            goal.meta_faturacao = payload.meta_faturacao
            goal.meta_contactos = payload.meta_contactos
            goal.meta_reunioes = payload.meta_reunioes
            goal.meta_angariacoes = payload.meta_angariacoes
            goal.meta_exclusivos = payload.meta_exclusivos
            goal.meta_visitas = payload.meta_visitas
            goal.meta_propostas = payload.meta_propostas
            goal.meta_cpcv = payload.meta_cpcv
            goal.meta_escrituras = payload.meta_escrituras
        else:
            goal = Goal(
                agencia_id=agencia_id,
                consultor_id=payload.consultor_id,
                ano=payload.ano,
                mes=payload.mes,
                meta_faturacao=payload.meta_faturacao,
                meta_contactos=payload.meta_contactos,
                meta_reunioes=payload.meta_reunioes,
                meta_angariacoes=payload.meta_angariacoes,
                meta_exclusivos=payload.meta_exclusivos,
                meta_visitas=payload.meta_visitas,
                meta_propostas=payload.meta_propostas,
                meta_cpcv=payload.meta_cpcv,
                meta_escrituras=payload.meta_escrituras,
            )
            db.add(goal)

        db.commit()
        db.refresh(goal)

        return GoalResponse(
            id=goal.id,
            agencia_id=goal.agencia_id,
            consultor_id=goal.consultor_id,
            consultor_nome=consultor.nome,
            ano=goal.ano,
            mes=goal.mes,
            meta_faturacao=goal.meta_faturacao,
            meta_contactos=goal.meta_contactos,
            meta_reunioes=goal.meta_reunioes,
            meta_angariacoes=goal.meta_angariacoes,
            meta_exclusivos=goal.meta_exclusivos,
            meta_visitas=goal.meta_visitas,
            meta_propostas=goal.meta_propostas,
            meta_cpcv=goal.meta_cpcv,
            meta_escrituras=goal.meta_escrituras,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )

    @staticmethod
    def list_goals(
        db: Session,
        agencia_id: int,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
        consultor_id: Optional[int] = None,
    ) -> List[GoalResponse]:
        """Lista metas com filtros opcionais de ano, mês e consultor."""
        query = db.query(Goal).filter(Goal.agencia_id == agencia_id)
        if ano:
            query = query.filter(Goal.ano == ano)
        if mes:
            query = query.filter(Goal.mes == mes)
        if consultor_id:
            query = query.filter(Goal.consultor_id == consultor_id)

        goals = query.all()
        return [
            GoalResponse(
                id=g.id,
                agencia_id=g.agencia_id,
                consultor_id=g.consultor_id,
                consultor_nome=g.consultor.nome if g.consultor else None,
                ano=g.ano,
                mes=g.mes,
                meta_faturacao=g.meta_faturacao,
                meta_contactos=g.meta_contactos,
                meta_reunioes=g.meta_reunioes,
                meta_angariacoes=g.meta_angariacoes,
                meta_exclusivos=g.meta_exclusivos,
                meta_visitas=g.meta_visitas,
                meta_propostas=g.meta_propostas,
                meta_cpcv=g.meta_cpcv,
                meta_escrituras=g.meta_escrituras,
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
            for g in goals
        ]

    # ==========================================
    # Operações de Oportunidades (Pipeline Deals)
    # ==========================================

    @staticmethod
    def create_pipeline_deal(db: Session, agencia_id: int, payload: PipelineDealCreate, user_id: int) -> PipelineDealResponse:
        """Cria uma nova oportunidade no pipeline da agência."""
        target_consultor_id = payload.consultor_id or user_id

        consultor = db.query(User).filter(
            User.id == target_consultor_id,
            User.agencia_id == agencia_id,
        ).first()

        if not consultor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultor não encontrado.")

        # Validação opcional de imóvel
        property_obj = None
        if payload.property_id:
            property_obj = db.query(Property).filter(
                Property.id == payload.property_id,
                Property.agencia_id == agencia_id,
            ).first()
            if not property_obj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imóvel não encontrado na carteira da agência.")

        deal = PipelineDeal(
            agencia_id=agencia_id,
            consultor_id=target_consultor_id,
            property_id=payload.property_id,
            cliente_nome=payload.cliente_nome,
            cliente_telefone=payload.cliente_telefone,
            tipo_negocio=payload.tipo_negocio,
            valor_imovel=payload.valor_imovel,
            comissao_estimada=payload.comissao_estimada,
            fase=payload.fase,
            probabilidade=payload.probabilidade,
            data_prevista_fecho=payload.data_prevista_fecho,
            proxima_acao=payload.proxima_acao,
            data_proxima_acao=payload.data_proxima_acao,
            ativo=payload.ativo,
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)

        return PipelineDealResponse(
            id=deal.id,
            agencia_id=deal.agencia_id,
            consultor_id=deal.consultor_id,
            consultor_nome=consultor.nome,
            property_id=deal.property_id,
            property_titulo=property_obj.titulo if property_obj else None,
            cliente_nome=deal.cliente_nome,
            cliente_telefone=deal.cliente_telefone,
            tipo_negocio=deal.tipo_negocio,
            valor_imovel=deal.valor_imovel,
            comissao_estimada=deal.comissao_estimada,
            comissao_ponderada=Decimal(str(deal.comissao_estimada)) * (Decimal(str(deal.probabilidade)) / Decimal("100")),
            fase=deal.fase,
            probabilidade=deal.probabilidade,
            data_prevista_fecho=deal.data_prevista_fecho,
            proxima_acao=deal.proxima_acao,
            data_proxima_acao=deal.data_proxima_acao,
            ativo=deal.ativo,
            created_at=deal.created_at,
            updated_at=deal.updated_at,
        )

    @staticmethod
    def list_pipeline_deals(
        db: Session,
        agencia_id: int,
        consultor_id: Optional[int] = None,
        fase: Optional[str] = None,
        ativo_apenas: bool = True,
    ) -> List[PipelineDealResponse]:
        """Lista oportunidades ativas com filtros opcionais de consultor e fase."""
        query = db.query(PipelineDeal).filter(PipelineDeal.agencia_id == agencia_id)
        if ativo_apenas:
            query = query.filter(PipelineDeal.ativo.is_(True))
        if consultor_id:
            query = query.filter(PipelineDeal.consultor_id == consultor_id)
        if fase:
            query = query.filter(PipelineDeal.fase == fase)

        deals = query.order_by(PipelineDeal.created_at.desc()).all()
        return [
            PipelineDealResponse(
                id=d.id,
                agencia_id=d.agencia_id,
                consultor_id=d.consultor_id,
                consultor_nome=d.consultor.nome if d.consultor else None,
                property_id=d.property_id,
                property_titulo=d.property.titulo if d.property else None,
                cliente_nome=d.cliente_nome,
                cliente_telefone=d.cliente_telefone,
                tipo_negocio=d.tipo_negocio,
                valor_imovel=d.valor_imovel,
                comissao_estimada=d.comissao_estimada,
                comissao_ponderada=Decimal(str(d.comissao_estimada)) * (Decimal(str(d.probabilidade)) / Decimal("100")),
                fase=d.fase,
                probabilidade=d.probabilidade,
                data_prevista_fecho=d.data_prevista_fecho,
                proxima_acao=d.proxima_acao,
                data_proxima_acao=d.data_proxima_acao,
                ativo=d.ativo,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in deals
        ]

    @staticmethod
    def update_pipeline_deal(
        db: Session,
        agencia_id: int,
        deal_id: int,
        payload: PipelineDealUpdate,
    ) -> PipelineDealResponse:
        """Atualiza dados, fase ou probabilidade de um negócio no pipeline."""
        deal = db.query(PipelineDeal).filter(
            PipelineDeal.id == deal_id,
            PipelineDeal.agencia_id == agencia_id,
        ).first()

        if not deal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")

        for campo, valor in payload.model_dump(exclude_unset=True).items():
            setattr(deal, campo, valor)

        db.commit()
        db.refresh(deal)

        return PipelineDealResponse(
            id=deal.id,
            agencia_id=deal.agencia_id,
            consultor_id=deal.consultor_id,
            consultor_nome=deal.consultor.nome if deal.consultor else None,
            property_id=deal.property_id,
            property_titulo=deal.property.titulo if deal.property else None,
            cliente_nome=deal.cliente_nome,
            cliente_telefone=deal.cliente_telefone,
            tipo_negocio=deal.tipo_negocio,
            valor_imovel=deal.valor_imovel,
            comissao_estimada=deal.comissao_estimada,
            comissao_ponderada=Decimal(str(deal.comissao_estimada)) * (Decimal(str(deal.probabilidade)) / Decimal("100")),
            fase=deal.fase,
            probabilidade=deal.probabilidade,
            data_prevista_fecho=deal.data_prevista_fecho,
            proxima_acao=deal.proxima_acao,
            data_proxima_acao=deal.data_proxima_acao,
            ativo=deal.ativo,
            created_at=deal.created_at,
            updated_at=deal.updated_at,
        )

    @staticmethod
    def delete_pipeline_deal(db: Session, agencia_id: int, deal_id: int) -> dict:
        """Remove ou arquiva uma oportunidade do pipeline."""
        deal = db.query(PipelineDeal).filter(
            PipelineDeal.id == deal_id,
            PipelineDeal.agencia_id == agencia_id,
        ).first()

        if not deal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")

        db.delete(deal)
        db.commit()
        return {"sucesso": True, "mensagem": "Oportunidade removida com sucesso."}
