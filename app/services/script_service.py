"""
Serviço de Negócios para Geração de Roteiros de Vídeo Curto - Fecho (fecho.pt).
Conforme FSD e DESIGN:
- Geração em 3 blocos obrigatórios: Gancho, 2 Destaques e CTA.
- Objetivos comerciais: Angariação, Baixa de Preço e Open House.
- Adaptação ao mercado imobiliário português de luxo e alta performance.
- Respeito estrito ao isolamento multi-tenant por agencia_id.
"""
from datetime import datetime, timezone
import math
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.property import Property
from app.models.user import User
from app.schemas.script_schema import (
    ScriptObjectiveEnum,
    ScriptObjectiveInfo,
    ScriptGenerateRequest,
    ScriptBlockResponse,
    ScriptResponse,
)


class ScriptService:
    """Motor de geração de roteiros de marketing imobiliário."""

    OBJETIVOS_INFO: Dict[ScriptObjectiveEnum, ScriptObjectiveInfo] = {
        ScriptObjectiveEnum.ANGARIACAO: ScriptObjectiveInfo(
            id="angariacao",
            nome="Angariação / Novo Imóvel",
            descricao="Apresentação exclusiva de um imóvel recém-chegado à carteira da agência.",
            badge="Novo no Mercado"
        ),
        ScriptObjectiveEnum.BAIXA_PRECO: ScriptObjectiveInfo(
            id="baixa_preco",
            nome="Baixa de Preço / Oportunidade",
            descricao="Comunicação assertiva de reajuste de valor e oportunidade imediata de fecho.",
            badge="Oportunidade"
        ),
        ScriptObjectiveEnum.OPEN_HOUSE: ScriptObjectiveInfo(
            id="open_house",
            nome="Open House / Portas Abertas",
            descricao="Convite direto e exclusivo para evento presencial de visita no imóvel.",
            badge="Portas Abertas"
        ),
    }

    @classmethod
    def get_objectives(cls) -> List[ScriptObjectiveInfo]:
        """Retorna os objetivos comerciais suportados pelo gerador de roteiros."""
        return list(cls.OBJETIVOS_INFO.values())

    @classmethod
    def format_currency(cls, value: float) -> str:
        """Formata valores numéricos para o padrão monetário português (€ X.XXX.XXX)."""
        val_int = int(round(value))
        formatted = f"{val_int:,}".replace(",", ".")
        return f"{formatted} €"

    @classmethod
    def calculate_reading_time_seconds(cls, text: str, wpm: int = 140) -> int:
        """Estima o tempo de leitura oral em segundos baseado na média de 140 palavras/minuto."""
        words = len(text.split())
        if words == 0:
            return 0
        seconds = math.ceil((words / wpm) * 60)
        return max(seconds, 5)

    @classmethod
    def generate_script(
        cls,
        db: Session,
        request: ScriptGenerateRequest,
        current_user: User,
    ) -> ScriptResponse:
        """
        Gera um roteiro em 3 blocos (Gancho, 2 Destaques e CTA) para o imóvel especificado,
        validando o isolamento multi-tenant por agencia_id.
        """
        property_obj = (
            db.query(Property)
            .filter(
                Property.id == request.property_id,
                Property.agencia_id == current_user.agencia_id
            )
            .first()
        )

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imóvel #{request.property_id} não encontrado na sua agência."
            )

        # Extração e normalização de atributos do imóvel
        titulo = property_obj.titulo or "Imóvel Exclusivo"
        tipologia = property_obj.tipologia or "Imóvel"
        preco_val = float(property_obj.preco) if property_obj.preco else 0.0
        preco_formatado = cls.format_currency(preco_val)
        
        localizacao_partes = []
        if property_obj.concelho:
            localizacao_partes.append(property_obj.concelho)
        elif property_obj.morada:
            localizacao_partes.append(property_obj.morada)
        if property_obj.distrito and property_obj.distrito != property_obj.concelho:
            localizacao_partes.append(property_obj.distrito)
        
        localizacao_str = ", ".join(localizacao_partes) if localizacao_partes else "Portugal"
        area_str = f"{int(property_obj.area_bruta)} m²" if property_obj.area_bruta else ""

        # Geração dos blocos com base no objetivo
        gancho, destaque_1, destaque_2, cta = cls._build_blocks(
            objetivo=request.objetivo,
            titulo=titulo,
            tipologia=tipologia,
            preco_formatado=preco_formatado,
            localizacao_str=localizacao_str,
            area_str=area_str,
            destaques_adicionais=request.destaques_adicionais,
            tom=request.tom or "sofisticado"
        )

        # Montagem dos blocos tipados
        t_gancho = cls.calculate_reading_time_seconds(gancho)
        t_d1 = cls.calculate_reading_time_seconds(destaque_1)
        t_d2 = cls.calculate_reading_time_seconds(destaque_2)
        t_destaques = t_d1 + t_d2
        t_cta = cls.calculate_reading_time_seconds(cta)

        blocos: List[ScriptBlockResponse] = [
            ScriptBlockResponse(
                ordem=1,
                chave="gancho",
                titulo="1. Gancho Magnético (0 a 5s)",
                tempo_estimado_segundos=t_gancho,
                conteudo=gancho
            ),
            ScriptBlockResponse(
                ordem=2,
                chave="destaques",
                titulo="2. Dois Destaques Irresistíveis (5 a 25s)",
                tempo_estimado_segundos=t_destaques,
                conteudo=f"{destaque_1}\n\n{destaque_2}"
            ),
            ScriptBlockResponse(
                ordem=3,
                chave="cta",
                titulo="3. Chamada para Ação (25 a 35s)",
                tempo_estimado_segundos=t_cta,
                conteudo=cta
            ),
        ]

        # Texto integral com pontuação e cadência perfeita para o Teleprompter
        texto_completo = (
            f"--- [1. GANCHO] ---\n"
            f"{gancho}\n\n"
            f"--- [2. DESTAQUES] ---\n"
            f"{destaque_1}\n\n"
            f"{destaque_2}\n\n"
            f"--- [3. CHAMADA PARA AÇÃO] ---\n"
            f"{cta}"
        )

        total_palavras = len((f"{gancho} {destaque_1} {destaque_2} {cta}").split())
        tempo_total = t_gancho + t_destaques + t_cta
        objetivo_info = cls.OBJETIVOS_INFO.get(request.objetivo)
        objetivo_label = objetivo_info.nome if objetivo_info else request.objetivo.value

        return ScriptResponse(
            property_id=property_obj.id,
            property_titulo=titulo,
            tipologia=tipologia,
            preco_formatado=preco_formatado,
            localizacao=localizacao_str,
            objetivo=request.objetivo,
            objetivo_label=objetivo_label,
            gancho=gancho,
            destaque_1=destaque_1,
            destaque_2=destaque_2,
            cta=cta,
            blocos=blocos,
            texto_completo=texto_completo,
            total_palavras=total_palavras,
            tempo_estimado_segundos=tempo_total,
            velocidade_wpm_referencia=140,
            criado_em=datetime.now(timezone.utc)
        )

    @classmethod
    def _build_blocks(
        cls,
        objetivo: ScriptObjectiveEnum,
        titulo: str,
        tipologia: str,
        preco_formatado: str,
        localizacao_str: str,
        area_str: str,
        destaques_adicionais: Optional[List[str]] = None,
        tom: str = "sofisticado"
    ) -> tuple[str, str, str, str]:
        """Gera as 4 partes essenciais dos 3 blocos estruturados."""
        
        area_texto = f" com {area_str}" if area_str else ""
        adicionais_str = (
            f" Entre os acabamentos, salienta-se: {', '.join(destaques_adicionais)}."
            if destaques_adicionais else ""
        )

        if objetivo == ScriptObjectiveEnum.ANGARIACAO:
            # Roteiro: Novo no Mercado / Angariação
            gancho = (
                f"Se está à procura de um {tipologia} de excelência em {localizacao_str}, "
                f"acaba de entrar no mercado uma oportunidade rara que vai querer conhecer agora mesmo."
            )
            destaque_1 = (
                f"Primeiro: a sua localização e configuração única{area_texto}. "
                f"Com uma exposição solar privilegiada e divisões amplas, "
                f"cada detalhe foi concebido para proporcionar o máximo conforto e bem-estar no seu dia a dia."
            )
            destaque_2 = (
                f"Segundo: uma proposta de valor irrepreensível por {preco_formatado}. "
                f"Seja para habitação própria ou património de família, este imóvel destaca-se "
                f"pela qualidade construtiva e elevado potencial de valorização.{adicionais_str}"
            )
            cta = (
                f"Não perca esta exclusividade. Envie-me agora uma mensagem privada ou clique no link da bio "
                f"para receber a ficha técnica detalhada e agendar a sua visita privada ainda esta semana."
            )

        elif objetivo == ScriptObjectiveEnum.BAIXA_PRECO:
            # Roteiro: Baixa de Preço / Oportunidade
            gancho = (
                f"Atenção a esta novidade de última hora em {localizacao_str}: "
                f"este fantástico {tipologia} acabou de ter um ajuste imediato de valor para {preco_formatado}!"
            )
            destaque_1 = (
                f"Primeiro destaque: valor abaixo da média praticada nesta zona de {localizacao_str}. "
                f"Estamos perante uma oportunidade clara de fecho rápido com retorno imediato de capital "
                f"para quem procura rentabilidade ou comprar no momento certo.{area_texto}"
            )
            destaque_2 = (
                f"Segundo destaque: prontidão absoluta. O imóvel encontra-se totalmente disponível, "
                f"com documentação validada pela nossa agência e condições ideais para escritura imediata.{adicionais_str}"
            )
            cta = (
                f"Imóveis com este nível de ajuste de preço fecham em poucos dias. "
                f"Fale comigo diretamente no WhatsApp através do botão abaixo para agendar a sua visita antes que seja reservado."
            )

        elif objetivo == ScriptObjectiveEnum.OPEN_HOUSE:
            # Roteiro: Open House / Portas Abertas
            gancho = (
                f"Este fim de semana abrimos as portas de um dos imóveis mais desejados de {localizacao_str}: "
                f"está convidado para o Open House exclusivo deste {tipologia}!"
            )
            destaque_1 = (
                f"O que vai poder experienciar no local: sentir a luz natural deste espaço{area_texto}, "
                f"conhecer a tranquilidade da zona e apreciar ao vivo os acabamentos requintados que as fotos não conseguem transmitir.{adicionais_str}"
            )
            destaque_2 = (
                f"Além disso, a nossa equipa estará presente para lhe entregar em mãos a simulação exata "
                f"dos custos de IMT, Imposto do Selo e condições de financiamento bancário para o valor de {preco_formatado}."
            )
            cta = (
                f"O acesso ao Open House requer confirmação prévia para garantir um atendimento personalizado. "
                f"Responda a este vídeo ou envie uma mensagem direta agora mesmo para reservar o seu horário de visita."
            )

        else:
            # Fallback seguro
            gancho = f"Conheça este magnífico {tipologia} em {localizacao_str} por {preco_formatado}."
            destaque_1 = f"Localização privilegiada{area_texto} com acabamentos de elevado padrão."
            destaque_2 = f"Excelente oportunidade de investimento.{adicionais_str}"
            cta = "Contacte-nos hoje mesmo para agendar a sua visita."

        return gancho, destaque_1, destaque_2, cta
