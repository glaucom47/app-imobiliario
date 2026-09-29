"""
Serviço de Domínio para Gestão de Leads, Captação e Angariação - Fecho (fecho.pt).
Conforme FSD (Seção 6):
- Isolamento estrito por agencia_id;
- Orquestração de scrapers (e-leiloes.pt e OLX);
- Conversão atômica em 1 clique gerando 'Property' com status 'Ativo';
- Governança RGPD: verificação de lista de oposição (LeadBlacklist) e mascaramento de dados;
- Registro de auditoria em audit_logs.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.lead import LeadAngariacao, LeadBlacklist
from app.models.log import Log
from app.models.property import Property
from app.models.user import User
from app.schemas.lead_schema import (
    LeadCreate,
    LeadStatsResponse,
    LeadUpdate,
)
from app.services.scrapers.base_scraper import BaseScraper
from app.services.scrapers.eleiloes_scraper import EleiloesScraper
from app.services.scrapers.olx_scraper import OlxScraper


class LeadService:
    """Regras de negócio e ciclo de vida das oportunidades de angariação."""

    @staticmethod
    def listar_leads(
        agencia_id: int,
        fonte: Optional[str] = None,
        status: Optional[str] = None,
        concelho: Optional[str] = None,
        tipologia: Optional[str] = None,
        consultor_id: Optional[int] = None,
        busca: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        db: Session = None,
    ) -> Tuple[int, List[LeadAngariacao]]:
        """Lista as oportunidades de captação da agência com paginação e filtros."""
        query = db.query(LeadAngariacao).filter(LeadAngariacao.agencia_id == agencia_id)

        if fonte:
            query = query.filter(LeadAngariacao.fonte == fonte.lower())
        if status:
            query = query.filter(LeadAngariacao.status == status)
        if concelho:
            query = query.filter(func.lower(LeadAngariacao.concelho).like(f"%{concelho.lower().strip()}%"))
        if tipologia:
            query = query.filter(LeadAngariacao.tipologia == tipologia)
        if consultor_id:
            query = query.filter(LeadAngariacao.consultor_atribuido_id == consultor_id)
        if busca:
            termo = f"%{busca.lower().strip()}%"
            query = query.filter(
                or_(
                    func.lower(LeadAngariacao.titulo).like(termo),
                    func.lower(LeadAngariacao.concelho).like(termo),
                    func.lower(LeadAngariacao.morada_aproximada).like(termo),
                    func.lower(LeadAngariacao.referencia_externa).like(termo),
                )
            )

        total = query.count()
        items = query.order_by(LeadAngariacao.created_at.desc()).offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def obter_lead(lead_id: int, agencia_id: int, db: Session) -> Optional[LeadAngariacao]:
        """Recupera uma oportunidade validando o isolamento de agência."""
        return (
            db.query(LeadAngariacao)
            .filter(LeadAngariacao.id == lead_id, LeadAngariacao.agencia_id == agencia_id)
            .first()
        )

    @staticmethod
    def _telefone_em_oposicao(agencia_id: int, telefone: Optional[str], db: Session) -> bool:
        """Verifica se o número de telefone está cadastrado na lista de oposição RGPD."""
        if not telefone:
            return False
        # Remove caracteres de formatação para comparação limpa
        tel_limpo = telefone.replace(" ", "").replace("-", "").replace("+351", "")
        blacklist = db.query(LeadBlacklist).filter(LeadBlacklist.agencia_id == agencia_id).all()
        for item in blacklist:
            item_limpo = item.telefone.replace(" ", "").replace("-", "").replace("+351", "")
            if item_limpo and item_limpo == tel_limpo:
                return True
        return False

    @classmethod
    def criar_ou_atualizar_lead(
        cls,
        agencia_id: int,
        dados: Dict[str, Any],
        db: Session,
    ) -> LeadAngariacao:
        """Cria uma nova oportunidade ou atualiza se já existir referência para a agência."""
        telefone = dados.get("telefone_contacto")
        if cls._telefone_em_oposicao(agencia_id, telefone, db):
            raise ValueError(
                "Contacto telefónico em oposição formal ao tratamento de dados (RGPD). "
                "Captação bloqueada para esta agência."
            )

        existente = (
            db.query(LeadAngariacao)
            .filter(
                LeadAngariacao.agencia_id == agencia_id,
                LeadAngariacao.fonte == dados["fonte"],
                LeadAngariacao.referencia_externa == dados["referencia_externa"],
            )
            .first()
        )

        if existente:
            # Não sobrescreve se o status atual for 'Convertido' ou 'Oposicao_RGPD'
            if existente.status not in ("Convertido", "Oposicao_RGPD"):
                existente.preco_solicitado = dados.get("preco_solicitado", existente.preco_solicitado)
                existente.valor_minimo_abertura = dados.get("valor_minimo_abertura", existente.valor_minimo_abertura)
                existente.titulo = dados.get("titulo", existente.titulo)
                existente.descricao = dados.get("descricao", existente.descricao)
                existente.data_limite_leilao = dados.get("data_limite_leilao", existente.data_limite_leilao)
                db.commit()
                db.refresh(existente)
            return existente

        nova_lead = LeadAngariacao(
            agencia_id=agencia_id,
            consultor_atribuido_id=dados.get("consultor_atribuido_id"),
            fonte=dados["fonte"],
            referencia_externa=dados["referencia_externa"],
            url_origem=dados["url_origem"],
            titulo=dados["titulo"],
            descricao=dados.get("descricao"),
            tipologia=dados.get("tipologia") or "T2",
            preco_solicitado=dados["preco_solicitado"],
            valor_minimo_abertura=dados.get("valor_minimo_abertura"),
            distrito=dados.get("distrito"),
            concelho=dados.get("concelho"),
            freguesia=dados.get("freguesia"),
            morada_aproximada=dados.get("morada_aproximada"),
            nome_contacto=dados.get("nome_contacto"),
            telefone_contacto=dados.get("telefone_contacto"),
            tipo_anunciante=dados.get("tipo_anunciante", "Particular"),
            status=dados.get("status", "Novo"),
            data_limite_leilao=dados.get("data_limite_leilao"),
            notas_prospeccao=dados.get("notas_prospeccao"),
        )
        db.add(nova_lead)
        db.commit()
        db.refresh(nova_lead)
        return nova_lead

    @classmethod
    def criar_lead_manual(
        cls,
        agencia_id: int,
        payload: LeadCreate,
        db: Session,
    ) -> LeadAngariacao:
        """Insere manualmente uma oportunidade de captação."""
        dados = payload.model_dump()
        return cls.criar_ou_atualizar_lead(agencia_id, dados, db)

    @classmethod
    def extrair_por_url(
        cls,
        agencia_id: int,
        url: str,
        consultor_id: Optional[int],
        db: Session,
    ) -> LeadAngariacao:
        """Extrai dados diretamente da URL informada (e-leilões ou OLX)."""
        url_lower = url.lower()
        if "e-leiloes.pt" in url_lower:
            scraper = EleiloesScraper()
        elif "olx.pt" in url_lower:
            scraper = OlxScraper()
        else:
            raise ValueError("URL não suportada. O Fecho suporta links do 'e-leiloes.pt' e do 'olx.pt'.")

        dados = scraper.extrair_por_url(url)
        if not dados:
            raise ValueError("Não foi possível extrair dados do imóvel no link fornecido.")

        if consultor_id:
            dados["consultor_atribuido_id"] = consultor_id

        return cls.criar_ou_atualizar_lead(agencia_id, dados, db)

    @classmethod
    def executar_varredura(
        cls,
        agencia_id: int,
        concelho: Optional[str] = None,
        distrito: Optional[str] = None,
        fonte: Optional[str] = None,
        db: Session = None,
    ) -> int:
        """
        Executa a varredura nas fontes abertas prioritárias para a zona da agência.
        Retorna o total de novas oportunidades salvas.
        """
        scrapers = []
        f_norm = (fonte or "").lower()

        if f_norm in ("e-leiloes", "todos", ""):
            scrapers.append(EleiloesScraper())
        if f_norm in ("olx", "todos", ""):
            scrapers.append(OlxScraper())

        novos_cadastrados = 0
        for scraper in scrapers:
            oportunidades = scraper.buscar_oportunidades(concelho=concelho, distrito=distrito, limite=10)
            for item in oportunidades:
                try:
                    cls.criar_ou_atualizar_lead(agencia_id, item, db)
                    novos_cadastrados += 1
                except ValueError:
                    # Ignora se estiver na blacklist RGPD
                    continue

        return novos_cadastrados

    @staticmethod
    def converter_em_imovel(
        lead_id: int,
        consultor_id: int,
        agencia_id: int,
        regiao_fiscal: Optional[str] = None,
        db: Session = None,
    ) -> Property:
        """
        Conversão em 1 clique:
        Instancia novo Property na carteira com status 'Ativo', atualiza a lead para 'Convertido'
        e vincula o ID do imóvel gerado. Operação atômica.
        """
        lead = (
            db.query(LeadAngariacao)
            .filter(LeadAngariacao.id == lead_id, LeadAngariacao.agencia_id == agencia_id)
            .first()
        )
        if not lead:
            raise ValueError("Oportunidade de angariação não encontrada.")

        if lead.status == "Convertido":
            raise ValueError(f"Esta oportunidade já se encontra convertida (Imóvel ID #{lead.imovel_convertido_id}).")

        if lead.status == "Oposicao_RGPD":
            raise ValueError("Não é possível converter oportunidade com oposição de tratamento RGPD.")

        # Determina a região fiscal (continente, madeira, acores)
        r_fiscal = (
            regiao_fiscal
            or BaseScraper.detectar_regiao_fiscal(lead.distrito, lead.concelho)
        )
        if r_fiscal not in ("continente", "madeira", "acores"):
            r_fiscal = "continente"

        # Garante dados de proprietário não nulos para conformidade com a entidade Property
        nome_prop = lead.nome_contacto.strip() if lead.nome_contacto else f"Proprietário ({lead.tipo_anunciante})"
        tel_prop = lead.telefone_contacto.strip() if lead.telefone_contacto else "+351 900 000 000"

        # Instancia novo imóvel ativo da carteira
        novo_imovel = Property(
            agencia_id=agencia_id,
            consultor_id=consultor_id,
            titulo=lead.titulo,
            descricao=lead.descricao or f"Captado via {lead.fonte.upper()} ({lead.referencia_externa})",
            tipologia=lead.tipologia or "T2",
            preco=lead.preco_solicitado,
            morada=lead.morada_aproximada or lead.titulo,
            concelho=lead.concelho or "Lisboa",
            distrito=lead.distrito or "Lisboa",
            regiao_fiscal=r_fiscal,
            status="Ativo",  # Conforme FSD: status inicial estrito
            nome_proprietario=nome_prop,
            telefone_proprietario=tel_prop,
        )

        db.add(novo_imovel)
        db.flush()  # Gera novo_imovel.id

        # Atualiza a lead para Convertido
        lead.status = "Convertido"
        lead.imovel_convertido_id = novo_imovel.id
        lead.consultor_atribuido_id = consultor_id

        # Registra trilha de auditoria
        log_entry = Log(
            agencia_id=agencia_id,
            user_id=consultor_id,
            acao="CONVERTER_LEAD_EM_IMOVEL",
            entidade="lead",
            entidade_id=lead.id,
            detalhes=(
                f"Lead #{lead.id} ({lead.fonte}: {lead.referencia_externa}) convertida no "
                f"imóvel #{novo_imovel.id} ('{novo_imovel.titulo}')."
            ),
        )
        db.add(log_entry)

        db.commit()
        db.refresh(novo_imovel)
        return novo_imovel

    @staticmethod
    def atualizar_status(
        lead_id: int,
        agencia_id: int,
        novo_status: str,
        notas: Optional[str],
        db: Session,
    ) -> LeadAngariacao:
        """Transita status da prospecção de forma controlada."""
        lead = (
            db.query(LeadAngariacao)
            .filter(LeadAngariacao.id == lead_id, LeadAngariacao.agencia_id == agencia_id)
            .first()
        )
        if not lead:
            raise ValueError("Oportunidade não encontrada.")

        if lead.status == "Convertido" and novo_status != "Convertido":
            raise ValueError("Não é permitido reverter o status de uma oportunidade já convertida em imóvel.")

        lead.status = novo_status
        if notas:
            lead.notas_prospeccao = notas

        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def aplicar_oposicao_rgpd(
        lead_id: int,
        agencia_id: int,
        user_id: int,
        motivo: Optional[str],
        db: Session,
    ) -> LeadAngariacao:
        """
        Registra a oposição expressa do titular (Art. 21 RGPD):
        1. Insere o número de telefone na tabela de blacklist da agência;
        2. Mascara de forma irreversível os dados de contato na lead;
        3. Altera status para 'Oposicao_RGPD';
        4. Registra evento de conformidade na trilha de auditoria.
        """
        lead = (
            db.query(LeadAngariacao)
            .filter(LeadAngariacao.id == lead_id, LeadAngariacao.agencia_id == agencia_id)
            .first()
        )
        if not lead:
            raise ValueError("Oportunidade não encontrada.")

        telefone_original = lead.telefone_contacto
        motivo_final = motivo or "Oposição expressa manifestada pelo proprietário (RGPD)"

        # Insere na blacklist se houver telefone
        if telefone_original and telefone_original != "000000000":
            ja_na_lista = (
                db.query(LeadBlacklist)
                .filter(LeadBlacklist.agencia_id == agencia_id, LeadBlacklist.telefone == telefone_original)
                .first()
            )
            if not ja_na_lista:
                black = LeadBlacklist(
                    agencia_id=agencia_id,
                    telefone=telefone_original,
                    motivo=motivo_final,
                )
                db.add(black)

        # Anonimiza os dados de contato do particular
        lead.status = "Oposicao_RGPD"
        lead.nome_contacto = "Proprietário com Oposição RGPD"
        lead.telefone_contacto = "000000000"
        lead.notas_prospeccao = f"[OPOSIÇÃO RGPD registada em {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}]: {motivo_final}"

        # Trilha de auditoria
        log_entry = Log(
            agencia_id=agencia_id,
            user_id=user_id,
            acao="OPOSICAO_RGPD_LEAD",
            entidade="lead",
            entidade_id=lead.id,
            detalhes=f"Oposição RGPD aplicada à lead #{lead.id}. Telefone incluído na blacklist de prospecção.",
        )
        db.add(log_entry)

        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def obter_estatisticas(agencia_id: int, db: Session) -> LeadStatsResponse:
        """Calcula os indicadores do módulo de captação para o Backoffice."""
        query_base = db.query(LeadAngariacao).filter(LeadAngariacao.agencia_id == agencia_id)

        total_oportunidades = query_base.count()
        total_eleiloes = query_base.filter(LeadAngariacao.fonte == "e-leiloes").count()
        total_olx = query_base.filter(LeadAngariacao.fonte == "olx").count()
        total_convertidas = query_base.filter(LeadAngariacao.status == "Convertido").count()

        taxa = 0.0
        if total_oportunidades > 0:
            taxa = round((total_convertidas / total_oportunidades) * 100, 1)

        return LeadStatsResponse(
            total_oportunidades=total_oportunidades,
            total_eleiloes=total_eleiloes,
            total_particulares_olx=total_olx,
            total_convertidas=total_convertidas,
            taxa_conversao_pct=taxa,
        )
