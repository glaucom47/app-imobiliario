"""
Serviço de Exportação de Dados em Formato Aberto CSV - Fecho (fecho.pt).

Conforme FSD e AGENTS.md:
- Exportações leves em formato aberto CSV (sem dependências pesadas de PDF);
- Codificação UTF-8 com BOM (\\ufeff) para abertura direta e correta no Microsoft Excel e Apple Numbers sem corrupção de acentos em português;
- Delimitador padrão ';' (padrão europeu / português);
- Higienização estrita contra CSV Injection (prefixação de aspa simples em valores que iniciam com '=', '+', '-', '@');
- Isolamento rigoroso por agencia_id.
"""
import csv
import io
from datetime import date, datetime
from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.objection import ObjectionTag, VisitObjection
from app.models.property import Property
from app.models.visit import Visit


def sanitize_csv_cell(value: Any) -> str:
    """
    Sanitiza uma célula CSV para evitar injeção de fórmulas (CSV Injection / Formula Injection).
    Se o valor começar com =, +, -, @, tab (\t) ou retorno de carro (\r), prefixa com aspa simples (').
    """
    if value is None:
        return ""
    raw = str(value)
    if raw and raw[0] in ("=", "+", "-", "@", "\t", "\r", "%"):
        return f"'{raw}"
    text = raw.strip()
    if text and text[0] in ("=", "+", "-", "@"):
        return f"'{text}"
    return text


def format_currency(value: Optional[float]) -> str:
    """Formata valor em euros com separador decimal por vírgula."""
    if value is None:
        return ""
    try:
        val_float = float(value)
        return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    except (ValueError, TypeError):
        return str(value)


def format_datetime(val: Optional[datetime]) -> str:
    """Formata datetime para 'DD/MM/AAAA HH:MM'."""
    if not val:
        return ""
    return val.strftime("%d/%m/%Y %H:%M")


def format_date(val: Optional[date]) -> str:
    """Formata date para 'DD/MM/AAAA'."""
    if not val:
        return ""
    return val.strftime("%d/%m/%Y")


class ExportService:
    """Serviço de geração de relatórios tabulares em formato CSV aberto."""

    @staticmethod
    def export_visitas_csv(db: Session, agencia_id: int) -> str:
        """
        Gera relatório CSV de visitas realizadas na agência com dados do consultor,
        imóvel, notas, duração de áudio e objeções levantadas.
        """
        output = io.StringIO()
        # UTF-8 BOM
        output.write("\ufeff")

        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        headers = [
            "ID Visita",
            "Data e Hora",
            "Consultor",
            "Email Consultor",
            "ID Imóvel",
            "Título do Imóvel",
            "Preço do Imóvel",
            "Cliente Comprador",
            "Contacto Cliente",
            "Duração Áudio (seg)",
            "Nível Interesse (1-5)",
            "Feedback Enviado Proprietário",
            "Objeções Identificadas",
            "Notas Estruturadas / Transcrição",
        ]
        writer.writerow(headers)

        visitas = (
            db.query(Visit)
            .filter(Visit.agencia_id == agencia_id)
            .order_by(Visit.data_visita.desc())
            .all()
        )

        for v in visitas:
            consultor_nome = v.consultor.nome if v.consultor else ""
            consultor_email = v.consultor.email if v.consultor else ""
            imovel_id = v.property.id if v.property else ""
            imovel_titulo = v.property.titulo if v.property else ""
            imovel_preco = format_currency(v.property.preco) if v.property else ""

            # Objeções associadas
            tags_list = []
            if v.objections:
                for obj in v.objections:
                    if obj.tag:
                        tags_list.append(obj.tag.tag)
            objecoes_str = ", ".join(tags_list)

            # Notas ou transcrição
            conteudo_notas = v.notas_estruturadas or v.transcricao or ""
            # Limpar quebras de linha para manter a linha do CSV limpa
            conteudo_limpo = " ".join(conteudo_notas.splitlines())

            row = [
                sanitize_csv_cell(v.id),
                sanitize_csv_cell(format_datetime(v.data_visita)),
                sanitize_csv_cell(consultor_nome),
                sanitize_csv_cell(consultor_email),
                sanitize_csv_cell(imovel_id),
                sanitize_csv_cell(imovel_titulo),
                sanitize_csv_cell(imovel_preco),
                sanitize_csv_cell(v.cliente_nome or "Não informado"),
                sanitize_csv_cell(v.cliente_telefone or "Não informado"),
                sanitize_csv_cell(v.audio_duracao_segundos if v.audio_duracao_segundos is not None else 0),
                sanitize_csv_cell(v.nivel_interesse if v.nivel_interesse is not None else ""),
                sanitize_csv_cell("Sim" if v.feedback_enviado_proprietario else "Não"),
                sanitize_csv_cell(objecoes_str),
                sanitize_csv_cell(conteudo_limpo),
            ]
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def export_imoveis_csv(db: Session, agencia_id: int) -> str:
        """
        Gera relatório CSV da carteira completa de imóveis da agência,
        incluindo estado, dados de angariação, comprador e valor.
        """
        output = io.StringIO()
        output.write("\ufeff")

        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        headers = [
            "ID Imóvel",
            "Título",
            "Tipologia",
            "Preço (€)",
            "Estado",
            "Região Fiscal",
            "Concelho",
            "Distrito",
            "Morada",
            "Área Bruta (m²)",
            "Consultor Responsável",
            "Nome Proprietário",
            "Contacto Proprietário",
            "Nome Comprador (se vendido)",
            "Contacto Comprador",
            "Data da Escritura",
            "Data de Angariação",
        ]
        writer.writerow(headers)

        imoveis = (
            db.query(Property)
            .filter(Property.agencia_id == agencia_id)
            .order_by(Property.created_at.desc())
            .all()
        )

        for p in imoveis:
            consultor_nome = p.consultor.nome if p.consultor else ""

            row = [
                sanitize_csv_cell(p.id),
                sanitize_csv_cell(p.titulo),
                sanitize_csv_cell(p.tipologia),
                sanitize_csv_cell(format_currency(p.preco)),
                sanitize_csv_cell(p.status),
                sanitize_csv_cell(p.regiao_fiscal),
                sanitize_csv_cell(p.concelho or ""),
                sanitize_csv_cell(p.distrito or ""),
                sanitize_csv_cell(p.morada or ""),
                sanitize_csv_cell(p.area_bruta if p.area_bruta is not None else ""),
                sanitize_csv_cell(consultor_nome),
                sanitize_csv_cell(p.nome_proprietario or ""),
                sanitize_csv_cell(p.telefone_proprietario or ""),
                sanitize_csv_cell(p.nome_comprador or ""),
                sanitize_csv_cell(p.telefone_comprador or ""),
                sanitize_csv_cell(format_date(p.data_escritura)),
                sanitize_csv_cell(format_datetime(p.created_at)),
            ]
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def export_objecoes_csv(db: Session, agencia_id: int, property_id: Optional[int] = None) -> str:
        """
        Gera relatório CSV consolidado de objeções por imóvel para renegociação de preços.
        """
        output = io.StringIO()
        output.write("\ufeff")

        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        headers = [
            "ID Imóvel",
            "Título do Imóvel",
            "Preço (€)",
            "Tag de Objeção",
            "Categoria",
            "Ocorrências Registradas",
            "Total Visitas do Imóvel",
            "Percentual de Incidência (%)",
        ]
        writer.writerow(headers)

        query = db.query(Property).filter(Property.agencia_id == agencia_id)
        if property_id:
            query = query.filter(Property.id == property_id)

        imoveis = query.all()

        for p in imoveis:
            total_visitas = len(p.visits)
            # Agrupar objeções deste imóvel
            contagem_tags = {}
            for v in p.visits:
                for obj in v.objections:
                    if obj.tag:
                        tag_key = (obj.tag.id, obj.tag.tag, obj.tag.categoria)
                        contagem_tags[tag_key] = contagem_tags.get(tag_key, 0) + 1

            if not contagem_tags:
                # Imóvel sem objeções registradas
                row = [
                    sanitize_csv_cell(p.id),
                    sanitize_csv_cell(p.titulo),
                    sanitize_csv_cell(format_currency(p.preco)),
                    sanitize_csv_cell("Nenhuma objeção registrada"),
                    sanitize_csv_cell("N/A"),
                    sanitize_csv_cell(0),
                    sanitize_csv_cell(total_visitas),
                    sanitize_csv_cell("0,0%"),
                ]
                writer.writerow(row)
            else:
                for (tag_id, tag_nome, categoria), total_ocorr in sorted(
                    contagem_tags.items(), key=lambda x: x[1], reverse=True
                ):
                    pct = (total_ocorr / total_visitas * 100) if total_visitas > 0 else 0.0
                    row = [
                        sanitize_csv_cell(p.id),
                        sanitize_csv_cell(p.titulo),
                        sanitize_csv_cell(format_currency(p.preco)),
                        sanitize_csv_cell(tag_nome),
                        sanitize_csv_cell(categoria),
                        sanitize_csv_cell(total_ocorr),
                        sanitize_csv_cell(total_visitas),
                        sanitize_csv_cell(f"{pct:.1f}%".replace(".", ",")),
                    ]
                    writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def export_contactos_csv(db: Session, agencia_id: int) -> str:
        """
        Gera relatório CSV dos contatos da Esfera de Influência / Pós-Venda.
        Respeita e reflete registros anonimizados conforme RGPD ('Cliente Anonimizado').
        """
        output = io.StringIO()
        output.write("\ufeff")

        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        headers = [
            "ID Contacto",
            "Nome",
            "Telemóvel",
            "Email",
            "Tipo de Contacto",
            "ID Imóvel Vinculado",
            "Data da Escritura",
            "Anos de Escritura",
            "Conformidade RGPD",
            "Consultor Responsável",
            "Data de Registo",
        ]
        writer.writerow(headers)

        contactos = (
            db.query(Contact)
            .filter(Contact.agencia_id == agencia_id)
            .order_by(Contact.data_escritura.desc().nullslast())
            .all()
        )

        today = date.today()

        for c in contactos:
            consultor_nome = c.consultor.nome if c.consultor else ""
            anos_escritura = ""
            if c.data_escritura:
                anos = today.year - c.data_escritura.year
                if (today.month, today.day) < (c.data_escritura.month, c.data_escritura.day):
                    anos -= 1
                anos_escritura = str(max(0, anos))

            rgpd_status = "Anonimizado (RGPD)" if (c.anonimizado or c.nome == "Cliente Anonimizado") else "Ativo"

            row = [
                sanitize_csv_cell(c.id),
                sanitize_csv_cell(c.nome),
                sanitize_csv_cell(c.telemovel or ""),
                sanitize_csv_cell(c.email or ""),
                sanitize_csv_cell(c.tipo),
                sanitize_csv_cell(c.property_id or ""),
                sanitize_csv_cell(format_date(c.data_escritura)),
                sanitize_csv_cell(anos_escritura),
                sanitize_csv_cell(rgpd_status),
                sanitize_csv_cell(consultor_nome),
                sanitize_csv_cell(format_datetime(c.created_at)),
            ]
            writer.writerow(row)

        return output.getvalue()
