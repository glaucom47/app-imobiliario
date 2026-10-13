"""
Serviço de Sincronização de Imóveis via API / Feeds XML e JSON de CRMs Externos (CRMSyncService).
Plataformas Suportadas: eGO Real Estate, Casafari CRM, X-Feed, Kyero, etc.

Regras de Negócio e Segurança:
1. Isolamento Multi-Tenant Estrito: Todos os imóveis são criados ou atualizados associando obrigatoriamente agencia_id.
2. Atualização Incremental: Imóveis são identificados por (agencia_id, referencia_externa).
3. Resiliência: Imóveis vendidos no Fecho não têm o status revertido por feeds automáticos (máquina de estados).
4. Auditoria: Registra o resumo da sincronização em audit_logs (Log).
"""
import json
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.property import Property
from app.models.user import User
from app.schemas.crm_sync_schema import CRMSyncRequest, CRMSyncResponse

logger = logging.getLogger(__name__)


class CRMSyncService:
    """Serviço de importação e sincronização de carteira imobiliária via XML/JSON."""

    @classmethod
    def fetch_feed_content(cls, request_data: CRMSyncRequest) -> str:
        """Obtém o conteúdo do feed a partir da URL ou do payload direto."""
        if request_data.feed_content and request_data.feed_content.strip():
            return request_data.feed_content.strip()

        if not request_data.feed_url or not request_data.feed_url.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="É necessário fornecer a URL do feed ('feed_url') ou o conteúdo direto ('feed_content')."
            )

        url = request_data.feed_url.strip()
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Fecho-CRM-Sync/1.0 (fecho.pt)"}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                content_bytes = response.read()
                return content_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Erro ao descarregar Feed CRM de {url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Não foi possível obter o feed remoto da URL informada: {str(e)}"
            )

    @classmethod
    def parse_feed_items(cls, raw_content: str, feed_type: str = "auto") -> List[Dict[str, Any]]:
        """
        Analisa e extrai os itens de imóveis do conteúdo bruto XML ou JSON.
        """
        raw_clean = raw_content.strip()
        items: List[Dict[str, Any]] = []

        # Tentar JSON se for explicitamente JSON ou se iniciar com '[' ou '{'
        if feed_type == "json" or (feed_type == "auto" and (raw_clean.startswith("[") or raw_clean.startswith("{"))):
            try:
                data = json.loads(raw_clean)
                if isinstance(data, list):
                    raw_items = data
                elif isinstance(data, dict):
                    # Buscar chaves comuns como 'properties', 'imoveis', 'items', 'data'
                    raw_items = data.get("properties") or data.get("imoveis") or data.get("items") or data.get("data") or [data]
                else:
                    raw_items = []

                for item in raw_items:
                    if isinstance(item, dict):
                        parsed = cls._normalize_property_dict(item)
                        if parsed:
                            items.append(parsed)
                return items
            except json.JSONDecodeError:
                if feed_type == "json":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Falha ao interpretar o conteúdo JSON do feed."
                    )

        # Tratar como XML
        try:
            # Remover declarações XML problemáticas ou namespaces complexos se necessário
            root = ET.fromstring(raw_clean)

            # Buscar elementos de imóveis em tags comuns (<property>, <imovel>, <item>, <ad>, <listing>)
            elements = (
                root.findall(".//property") or
                root.findall(".//imovel") or
                root.findall(".//item") or
                root.findall(".//ad") or
                root.findall(".//listing") or
                list(root)
            )

            for elem in elements:
                item_dict = cls._xml_element_to_dict(elem)
                parsed = cls._normalize_property_dict(item_dict)
                if parsed:
                    items.append(parsed)

            return items
        except ET.ParseError as pe:
            logger.error(f"Erro de parsing XML: {pe}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato XML inválido ou corrompido no feed: {str(pe)}"
            )

    @classmethod
    def _xml_element_to_dict(cls, elem: ET.Element) -> Dict[str, Any]:
        """Converte um elemento XML simples num dicionário Python."""
        result: Dict[str, Any] = {}
        for child in elem:
            tag = child.tag.split("}")[-1]  # Remove namespace se existir
            text = child.text.strip() if child.text else ""
            if len(child) > 0:
                result[tag] = cls._xml_element_to_dict(child)
            else:
                result[tag] = text
        # Incluir atributos do nó principal se houver ID
        if "id" in elem.attrib and "id" not in result:
            result["id"] = elem.attrib["id"]
        if "ref" in elem.attrib and "ref" not in result:
            result["ref"] = elem.attrib["ref"]
        return result

    @classmethod
    def _normalize_property_dict(cls, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normaliza as chaves e tipos de um dicionário extraído de XML/JSON."""
        if not isinstance(item, dict):
            return None

        # Identificação da referência externa
        ref = (
            item.get("referencia_externa") or
            item.get("referencia") or
            item.get("ref") or
            item.get("id") or
            item.get("reference") or
            item.get("code")
        )
        if not ref:
            return None

        ref_str = str(ref).strip()

        # Título
        titulo = (
            item.get("titulo") or
            item.get("title") or
            item.get("name") or
            item.get("headline") or
            f"Imóvel CRM #{ref_str}"
        )

        # Descrição
        descricao = item.get("descricao") or item.get("description") or item.get("details")

        # Preço
        raw_preco = item.get("preco") or item.get("price") or item.get("val_venda") or item.get("val_preco") or 0.0
        try:
            if isinstance(raw_preco, str):
                cleaned_price = re.sub(r"[^\d,\.]", "", raw_preco)
                if "," in cleaned_price and "." in cleaned_price:
                    cleaned_price = cleaned_price.replace(".", "").replace(",", ".")
                elif "," in cleaned_price:
                    cleaned_price = cleaned_price.replace(",", ".")
                elif "." in cleaned_price:
                    parts = cleaned_price.split(".")
                    if len(parts[-1]) == 3:
                        cleaned_price = "".join(parts)
                preco_val = float(cleaned_price) if cleaned_price else 100000.0
            else:
                preco_val = float(raw_preco)
        except ValueError:
            preco_val = 100000.0

        if preco_val <= 0:
            preco_val = 100000.0

        # Tipologia (T0..T5+, Moradia, Loja, etc.)
        raw_tip = str(item.get("tipologia") or item.get("type") or item.get("property_type") or "T2").strip().upper()
        if "MORADIA" in raw_tip or "VILLA" in raw_tip or "HOUSE" in raw_tip:
            tipologia = "Moradia"
        elif "TERRENO" in raw_tip or "PLOT" in raw_tip:
            tipologia = "Terreno"
        elif "LOJA" in raw_tip or "COMMERCIAL" in raw_tip:
            tipologia = "Loja"
        elif re.match(r"^T\d", raw_tip):
            tipologia = raw_tip[:3]
        else:
            tipologia = "T2"

        # Morada, Concelho, Distrito
        morada = item.get("morada") or item.get("address") or item.get("location") or item.get("street")
        concelho = item.get("concelho") or item.get("town") or item.get("city") or item.get("municipality")
        distrito = item.get("distrito") or item.get("district") or item.get("state") or item.get("region")

        # Região Fiscal
        regiao_raw = str(item.get("regiao_fiscal") or "").lower()
        if "madeira" in regiao_raw:
            regiao_fiscal = "madeira"
        elif "acores" in regiao_raw or "açores" in regiao_raw:
            regiao_fiscal = "acores"
        else:
            regiao_fiscal = "continente"

        # Área Bruta
        raw_area = item.get("area_bruta") or item.get("area") or item.get("built_area") or item.get("surface_area")
        area_bruta = None
        if raw_area:
            try:
                area_bruta = float(str(raw_area).replace(",", "."))
            except ValueError:
                area_bruta = None

        # Status ('Ativo', 'Reservado', 'Vendido')
        raw_status = str(item.get("status") or item.get("state") or "").strip().capitalize()
        if raw_status in ("Reservado", "Reserved"):
            status_val = "Reservado"
        elif raw_status in ("Vendido", "Sold"):
            status_val = "Vendido"
        else:
            status_val = "Ativo"

        # Dados do Proprietário / Contacto
        nome_prop = item.get("nome_proprietario") or item.get("owner_name") or item.get("contact_name") or "Agência / CRM Sync"
        tel_prop = item.get("telefone_proprietario") or item.get("owner_phone") or item.get("contact_phone") or "N/A"

        return {
            "referencia_externa": ref_str,
            "titulo": str(titulo)[:255],
            "descricao": str(descricao) if descricao else None,
            "tipologia": tipologia[:20],
            "preco": Decimal(str(round(preco_val, 2))),
            "morada": str(morada)[:255] if morada else None,
            "concelho": str(concelho)[:100] if concelho else None,
            "distrito": str(distrito)[:100] if distrito else None,
            "regiao_fiscal": regiao_fiscal,
            "area_bruta": Decimal(str(round(area_bruta, 2))) if area_bruta else None,
            "status": status_val,
            "nome_proprietario": str(nome_prop)[:255],
            "telefone_proprietario": str(tel_prop)[:50],
        }

    @classmethod
    def sync_properties(
        cls,
        db: Session,
        current_user: User,
        request_data: CRMSyncRequest
    ) -> CRMSyncResponse:
        """
        Executa a sincronização de imóveis para a agência do usuário autenticado.
        Garante o isolamento multi-tenant estrito (agencia_id).
        """
        agencia_id = current_user.agencia_id

        # 1. Resolver consultor responsável padrão
        target_consultor_id = current_user.id
        if request_data.default_consultor_id:
            consultor = db.query(User).filter(
                User.id == request_data.default_consultor_id,
                User.agencia_id == agencia_id,
                User.ativo == True
            ).first()
            if consultor:
                target_consultor_id = consultor.id

        # 2. Obter conteúdo do feed
        raw_content = cls.fetch_feed_content(request_data)

        # 3. Processar e extrair lista de itens
        items = cls.parse_feed_items(raw_content, request_data.feed_type or "auto")

        criados = 0
        atualizados = 0
        ignorados = 0
        erros: List[str] = []

        for item in items:
            ref_ext = item["referencia_externa"]
            try:
                # Buscar se o imóvel com esta referencia_externa já existe nesta agência
                existing_prop = db.query(Property).filter(
                    Property.agencia_id == agencia_id,
                    Property.referencia_externa == ref_ext
                ).first()

                if existing_prop:
                    # Atualização de imóvel existente
                    existing_prop.titulo = item["titulo"]
                    if item["descricao"]:
                        existing_prop.descricao = item["descricao"]
                    existing_prop.tipologia = item["tipologia"]
                    existing_prop.preco = item["preco"]
                    if item["morada"]:
                        existing_prop.morada = item["morada"]
                    if item["concelho"]:
                        existing_prop.concelho = item["concelho"]
                    if item["distrito"]:
                        existing_prop.distrito = item["distrito"]
                    existing_prop.regiao_fiscal = item["regiao_fiscal"]
                    if item["area_bruta"]:
                        existing_prop.area_bruta = item["area_bruta"]

                    # Atualiza status apenas se o imóvel ainda não foi transitado para 'Vendido' no Fecho
                    if existing_prop.status != "Vendido" and item["status"] in ("Ativo", "Reservado"):
                        existing_prop.status = item["status"]

                    atualizados += 1
                else:
                    # Cadastro de novo imóvel na agência
                    new_prop = Property(
                        agencia_id=agencia_id,
                        consultor_id=target_consultor_id,
                        referencia_externa=ref_ext,
                        titulo=item["titulo"],
                        descricao=item["descricao"],
                        tipologia=item["tipologia"],
                        preco=item["preco"],
                        morada=item["morada"],
                        concelho=item["concelho"],
                        distrito=item["distrito"],
                        regiao_fiscal=item["regiao_fiscal"],
                        area_bruta=item["area_bruta"],
                        status="Ativo",
                        nome_proprietario=item["nome_proprietario"],
                        telefone_proprietario=item["telefone_proprietario"],
                    )
                    db.add(new_prop)
                    criados += 1
            except Exception as ex:
                logger.warning(f"Erro ao processar imóvel ref '{ref_ext}': {ex}")
                erros.append(f"Ref '{ref_ext}': {str(ex)}")
                ignorados += 1

        db.commit()

        # 4. Registrar trilha de auditoria
        audit_log = Log(
            agencia_id=agencia_id,
            user_id=current_user.id,
            acao="sync_crm_feed",
            entidade="property",
            entidade_id=None,
            detalhes=f"Sincronização CRM: {criados} criados, {atualizados} atualizados, {ignorados} ignorados de {len(items)} itens no feed."
        )
        db.add(audit_log)
        db.commit()

        mensagem = f"Sincronização de carteira CRM efetuada com sucesso: {criados} imóveis novos cadastrados e {atualizados} imóveis atualizados."

        return CRMSyncResponse(
            sucesso=True,
            agencia_id=agencia_id,
            total_processados=len(items),
            imoveis_criados=criados,
            imoveis_atualizados=atualizados,
            imoveis_ignorados=ignorados,
            erros=erros,
            mensagem=mensagem
        )
