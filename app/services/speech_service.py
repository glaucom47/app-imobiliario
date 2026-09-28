"""
Serviço de Processamento de Voz, Transcrição e Extração Semântica - Fecho (fecho.pt).

Responsável por:
1. Extração semântica de nível de interesse (1 a 5) a partir do relato verbal da visita;
2. Mapeamento inteligente contra o catálogo corporativo de objeções padronizadas da agência;
3. Estruturação editorial das notas de campo para o ecrã de revisão (Human-in-the-Loop);
4. Geração de mensagem de prestação de contas formatada e Deep Link para WhatsApp do proprietário.
"""
import re
import urllib.parse
from typing import Dict, List, Optional, Tuple

from app.models.property import Property
from app.models.user import User
from app.models.visit import Visit


class SpeechService:
    """Orquestrador de inteligência de voz e análise semântica de visitas."""

    # Dicionário de termos para extração de nível de interesse (1 a 5)
    INTEREST_PATTERNS = [
        # Nível 5: Proposta Iminente / Entusiasmo Total
        (
            5,
            [
                r"\b(adorou|interessad[ií]ssim[oa]|vai avan[çc]ar|vai fazer proposta|fazer proposta|apaixonad[oa]|proposta formal|compra certa|fechar neg[oó]cio|comprar j[aá]|quer avan[çc]ar)\b"
            ],
        ),
        # Nível 4: Interesse Elevado / Forte Candidato
        (
            4,
            [
                r"\b(gostou muito|bastante interessad[oa]|forte candidat[oa]|boa impress[aã]o|quer voltar|segunda visita|agradou bastante|muito positiv[oa]|potencial comprador)\b"
            ],
        ),
        # Nível 2: Reticente / Baixo Interesse
        (
            2,
            [
                r"\b(achou caro|reticente|n[aã]o gostou muito|apertado|desapontad[oa]|dif[ií]cil|n[aã]o convenceu|achou pequeno|pouco interessad[oa])\b"
            ],
        ),
        # Nível 1: Descartado / Sem Interesse
        (
            1,
            [
                r"\b(descartou|rejeitou|odiei|odiaram|horr[ií]vel|fora de quest[aã]o|n[aã]o tem interesse|desistiu|n[aã]o quer|descartado completamente)\b"
            ],
        ),
        # Nível 3: Médio / Em Análise (padrão)
        (
            3,
            [
                r"\b(neutr[oa]|avalia[çc][aã]o|a pensar|razo[aá]vel|vai comparar|indecis[oa]|vai analisar|curios[oa]|gostou mas)\b"
            ],
        ),
    ]

    # Termos semânticos para identificação de objeções padronizadas
    OBJECTION_KEYWORDS: Dict[str, List[str]] = {
        "Preço Elevado": [
            "caro", "preço", "preco", "valor alto", "acima do mercado",
            "desconto", "renegociar", "custo elevado", "orçamento curto", "valor elevado"
        ],
        "Área Inferior ao Esperado": [
            "pequeno", "área", "area", "espaço reduzido", "quartos pequenos",
            "apertado", "metragem", "sem espaço", "dimensão reduzida"
        ],
        "Ruído da Rua / Zona Movimentada": [
            "barulho", "ruído", "ruido", "trânsito", "transito", "movimento",
            "estrada", "rua movimentada", "avenida barulhenta", "sonoro", "acústica"
        ],
        "Falta de Garagem / Estacionamento": [
            "garagem", "estacionamento", "estacionar", "sem lugar", "parqueamento",
            "sem garagem", "dificuldade de estacionar"
        ],
        "Exposição Solar Fraca": [
            "sol", "escuro", "luminosidade", "pouca luz", "frio", "virado a norte",
            "pouca claridade", "sombra"
        ],
        "Necessita de Obras Profundas": [
            "obras", "remodelação", "remodelacao", "reforma", "antigo", "degradado",
            "reparar", "infiltração", "infiltracao", "precisa obras", "gasto em obras"
        ],
        "Piso Elevado sem Elevador": [
            "escadas", "sem elevador", "quarto andar", "terceiro andar", "subir a pé",
            "subida", "sem ascensor"
        ],
    }

    @classmethod
    def analyze_transcript(
        cls,
        text: str,
        available_tags: Optional[List[Dict[str, any]]] = None,
    ) -> Tuple[int, List[str], List[int], str]:
        """
        Analisa o texto verbal extraído ou digitado.
        Retorna:
        - nivel_interesse (1 a 5)
        - detected_tag_names (lista de nomes de tags encontradas)
        - detected_tag_ids (lista de IDs das tags ativas da agência)
        - notas_estruturadas (resumo editorial em tópicos)
        """
        if not text or not text.strip():
            return 3, [], [], "• Visita realizada. Sem observações adicionais gravadas."

        cleaned_text = text.strip()
        lower_text = cleaned_text.lower()

        # 1. Determinação do nível de interesse (1 a 5)
        nivel_interesse = 3  # default
        for level, patterns in cls.INTEREST_PATTERNS:
            found = False
            for pattern in patterns:
                if re.search(pattern, lower_text, re.IGNORECASE):
                    nivel_interesse = level
                    found = True
                    break
            if found:
                break

        # 2. Identificação de Objeções
        detected_tag_names: List[str] = []
        for tag_name, keywords in cls.OBJECTION_KEYWORDS.items():
            for kw in keywords:
                # Busca por limite de palavra ou correspondência direta
                if kw in lower_text:
                    if tag_name not in detected_tag_names:
                        detected_tag_names.append(tag_name)
                    break

        # Mapeia para os IDs do catálogo da agência se fornecidos
        detected_tag_ids: List[int] = []
        if available_tags:
            for tag_dict in available_tags:
                tag_str = tag_dict.get("tag", "")
                tag_id = tag_dict.get("id")
                # Correspondência exata ou parcial de nome
                for det in detected_tag_names:
                    if det.lower() in tag_str.lower() or tag_str.lower() in det.lower():
                        if tag_id and tag_id not in detected_tag_ids:
                            detected_tag_ids.append(tag_id)

        # 3. Geração de Notas Estruturadas em tópicos
        sentences = [s.strip() for s in re.split(r"[.\n;]+", cleaned_text) if len(s.strip()) > 3]
        if sentences:
            structured_lines = [f"• {s}." if not s.endswith(".") else f"• {s}" for s in sentences]
            notas_estruturadas = "\n".join(structured_lines)
        else:
            notas_estruturadas = f"• {cleaned_text}"

        return nivel_interesse, detected_tag_names, detected_tag_ids, notas_estruturadas

    @classmethod
    def format_whatsapp_feedback(
        cls,
        propriedade: Property,
        consultor: User,
        nivel_interesse: Optional[int] = None,
        notas_estruturadas: Optional[str] = None,
        objection_names: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        """
        Gera o texto editorial refinado de prestação de contas ao proprietário
        e o respectivo Deep Link para o WhatsApp (api.whatsapp.com/send).
        """
        nome_proprietario = propriedade.nome_proprietario or "Proprietário(a)"
        telefone_proprietario = propriedade.telefone_proprietario or ""
        titulo_imovel = f"{propriedade.tipologia} • {propriedade.titulo}"
        nome_consultor = consultor.nome if consultor else "Consultor Imobiliário"

        # Mapeamento do nível de interesse para estrelas e rótulo verbal elegante
        interesse_map = {
            5: ("★ ★ ★ ★ ★", "Proposta Iminente / Entusiasmo Total"),
            4: ("★ ★ ★ ★ ☆", "Interesse Elevado / Forte Potencial"),
            3: ("★ ★ ★ ☆ ☆", "Interesse Médio / Em Avaliação Comparativa"),
            2: ("★ ★ ☆ ☆ ☆", "Interesse Baixo / Com Reservas"),
            1: ("★ ☆ ☆ ☆ ☆", "Sem Interesse / Não Enquadrado no Perfil"),
        }
        stars, label = interesse_map.get(nivel_interesse or 3, ("★ ★ ★ ☆ ☆", "Em Avaliação"))

        # Formatação das notas
        notas_texto = notas_estruturadas.strip() if notas_estruturadas else "Visita acompanhada e esclarecimento de dúvidas sobre o imóvel."

        # Seção de pontos de atenção / objeções
        pontos_atencao_bloco = ""
        if objection_names and len(objection_names) > 0:
            itens = "\n".join([f"  - {nome}" for nome in objection_names])
            pontos_atencao_bloco = f"\n• Pontos de Atenção Levantados:\n{itens}\n"

        mensagem = (
            f"Estimado(a) {nome_proprietario},\n\n"
            f"Partilho o resumo da visita realizada hoje ao seu imóvel ({titulo_imovel}):\n\n"
            f"• Nível de Interesse: {stars} ({label})\n\n"
            f"• Resumo da Visita:\n{notas_texto}\n"
            f"{pontos_atencao_bloco}\n"
            f"Seguimos a acompanhar este cliente com o devido rigor e manter-lhe-ei informado(a) sobre qualquer evolução ou proposta formal.\n\n"
            f"Com os melhores cumprimentos,\n"
            f"{nome_consultor}\n"
            f"Fecho (fecho.pt)"
        )

        # Sanitiza o telemóvel para formato numérico internacional
        phone_sanitized = re.sub(r"[^\d+]", "", telefone_proprietario)
        if phone_sanitized.startswith("+"):
            phone_sanitized = phone_sanitized[1:]

        encoded_text = urllib.parse.quote(mensagem)
        deep_link = f"https://api.whatsapp.com/send?phone={phone_sanitized}&text={encoded_text}" if phone_sanitized else f"https://api.whatsapp.com/send?text={encoded_text}"

        return mensagem, deep_link
