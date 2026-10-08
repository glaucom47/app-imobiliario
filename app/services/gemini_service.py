"""
Serviço de Integração com a API Google Gemini (google-genai) - MeuFecho (meufecho.pt).

Oferece suporte à geração de respostas inteligentes para consultores e diretores imobiliários,
com modo Mock / Simulador integrado para testes automatizados e execução sem chave configurada.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from config.config import settings

logger = logging.getLogger(__name__)

# Tenta importar o SDK oficial da Google GenAI
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False


SYSTEM_PROMPT = """Você é o Assistente Virtual Imobiliário inteligente do MeuFecho (meufecho.pt), especialista no mercado imobiliário em Portugal.

Suas diretrizes de atendimento:
- Responda em Português de Portugal (PT-PT) com tom profissional, elegante, claro e focado em resultados comerciais;
- Auxilie na criação de descrições atraentes de imóveis, argumentos de negociação e baixa de preço, scripts de vídeo curtos e esclarecimentos sobre tributação (IMT, Imposto do Selo, IMT Jovem - DL n.º 48-A/2024);
- Seja conciso e forneça valor prático imediato para o consultor ou diretor imobiliário;
- Não invente dados fiscais além das regras legais oficiais de Portugal."""


class GeminiService:
    """Serviço para gestão de interações com a API Google Gemini."""

    @classmethod
    def generate_response(
        cls,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        agencia_id: Optional[int] = None,
        force_mock: bool = False
    ) -> Tuple[str, bool]:
        """
        Gera resposta da IA utilizando a API oficial do Gemini ou o modo Mock/Simulador.

        Retorna:
            Tuple[str, bool]: (texto_da_resposta, foi_mock)
        """
        message_clean = (message or "").strip()
        if not message_clean:
            return "Por favor, indique uma pergunta ou instrução para o Assistente Imobiliário.", True

        # Verifica se deve acionar o modo Mock
        is_test_env = settings.ENVIRONMENT == "test"
        api_key = settings.GEMINI_API_KEY.strip()
        should_use_mock = force_mock or is_test_env or not api_key or not GENAI_AVAILABLE

        if not should_use_mock and api_key:
            try:
                client = genai.Client(api_key=api_key)
                
                # Constrói o prompt final incorporando o contexto do imóvel/visita se fornecido
                prompt_content = cls._build_prompt(message_clean, context)
                
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt_content,
                    config={
                        "system_instruction": SYSTEM_PROMPT,
                        "temperature": 0.7,
                    }
                )
                
                if response and response.text:
                    return response.text.strip(), False
            except Exception as e:
                logger.warning(f"Falha na chamada à API do Gemini ({e}). Ativando modo Mock de contingência.")
                # Fallback defensivo para mock se a API falhar ou cota for excedida

        # Execução via Modo Mock / Simulador inteligente
        mock_reply = cls._generate_mock_response(message_clean, context)
        return mock_reply, True

    @classmethod
    def _build_prompt(cls, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Estrutura o prompt enviando contexto de imóvel ou visita quando disponível."""
        if not context:
            return message

        context_parts = []
        if context.get("titulo"):
            context_parts.append(f"Imóvel: {context.get('titulo')}")
        if context.get("preco"):
            context_parts.append(f"Preço: {context.get('preco')} €")
        if context.get("tipologia"):
            context_parts.append(f"Tipologia: {context.get('tipologia')}")
        if context.get("morada") or context.get("concelho"):
            context_parts.append(f"Localização: {context.get('morada', '')} {context.get('concelho', '')}".strip())
        if context.get("notas_visita"):
            context_parts.append(f"Notas da Visita: {context.get('notas_visita')}")
        if context.get("objecoes"):
            context_parts.append(f"Objeções Registadas: {context.get('objecoes')}")

        if context_parts:
            header = "=== CONTEXTO DO IMÓVEL / VISITA ===\n" + "\n".join(context_parts) + "\n===================================\n\n"
            return header + f"Instrução do Utilizador: {message}"
        return message

    @classmethod
    def _generate_mock_response(cls, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Gera resposta simulada contextual em PT-PT de alta qualidade."""
        msg_lower = message.lower()
        prop_title = (context or {}).get("titulo", "este imóvel")

        if "descri" in msg_lower or "anúncio" in msg_lower or "anuncio" in msg_lower:
            return (
                f"✨ **Proposta de Anúncio Exclusivo - {prop_title}**\n\n"
                f"Apresentamos uma oportunidade singular no mercado imobiliário. {prop_title} "
                f"destaca-se pela sua excelente exposição solar, acabamentos contemporâneos e localização privilegiada.\n\n"
                f"**Destaques Principais:**\n"
                f"• Distribuição espacial otimizada com amplos espaços de convivência;\n"
                f"• Cozinha totalmente equipada e acabamentos de elevada qualidade;\n"
                f"• Proximidade aos principais acessos, transportes, comércio e serviços de referência.\n\n"
                f"Ideal tanto para habitação própria permanente quanto para investimento de elevada rentabilidade.\n"
                f"📱 *Agende já a sua visita no MeuFecho!*"
            )

        if "objeção" in msg_lower or "objecao" in msg_lower or "preço" in msg_lower or "baixar" in msg_lower or "negocia" in msg_lower:
            return (
                f"📊 **Argumentário de Renegociação de Preço com o Proprietário**\n\n"
                f"Com base nos feedbacks reais recolhidos nas visitas a **{prop_title}**:\n\n"
                f"1. **Evidência de Mercado:** Os compradores interessados reconhecem o potencial do imóvel, "
                f"mas apontam ajustamentos necessários no valor estipulado perante imóveis similares na zona.\n"
                f"2. **Estratégia Recomendada:** Propor uma revisão estratégica de preço para maximizar a atratividade "
                f"e fechar o negócio no prazo ideal de comercialização.\n"
                f"3. **Proposta de Ação:** Reajustar o valor em 5% a 8% para reativar o interesse dos compradores qualificados que já visitaram."
            )

        if "imt" in msg_lower or "selo" in msg_lower or "imposto" in msg_lower or "fiscal" in msg_lower:
            return (
                "⚖️ **Resumo Fiscal em Portugal (IMT e Selo)**\n\n"
                "• **IMT (Habitação Própria Permanente):** Isenção no Continente até ao 1º escalão legal, com taxas marginais progressivas nas faixas seguintes.\n"
                "• **IMT Jovem (DL n.º 48-A/2024):** Isenção total de IMT e Imposto do Selo para jovens até aos 35 anos na aquisição de HPP até ao limite fixado na lei.\n"
                "• **Imposto do Selo:** 0,8% sobre o valor da aquisição + 0,6% sobre o montante financiado em crédito habitação.\n\n"
                "💡 *Dica: Utilize a nossa Calculadora em Visita no PWA para obter os valores exatos instantaneamente e offline!*"
            )

        if "script" in msg_lower or "vídeo" in msg_lower or "video" in msg_lower or "reels" in msg_lower:
            return (
                f"🎬 **Roteiro de Vídeo Curto (3 Blocos) - {prop_title}**\n\n"
                f"**1. Gancho (0s - 5s):**\n"
                f"\"Procura o imóvel perfeito com localização premium? Venha conhecer {prop_title}!\"\n\n"
                f"**2. Destaques (5s - 20s):**\n"
                f"\"Áreas generosas, luz natural incrível e um padrão de conforto impecável para toda a família.\"\n\n"
                f"**3. Chamada à Ação - CTA (20s - 30s):**\n"
                f"\"Envie mensagem privada agora para agendar a sua visita antes que fique reservado!\""
            )

        return (
            f"🤖 **Assistente Imobiliário MeuFecho**\n\n"
            f"Olá! Estou pronto para apoiar a sua operação imobiliária em **{prop_title}**.\n\n"
            f"Como posso ajudar hoje?\n"
            f"• Redigir anúncios de marketing;\n"
            f"• Criar argumentos para renegociação de preços;\n"
            f"• Gerar scripts para vídeos e teleprompter;\n"
            f"• Esclarecer custos fiscais de IMT e Imposto do Selo."
        )
