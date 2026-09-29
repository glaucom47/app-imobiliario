"""
Classe Base e Utilitários para Scrapers de Captação e Angariação - Fecho (fecho.pt).
"""
import re
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional


class BaseScraper(ABC):
    """Interface padrão para scrapers de fontes abertas no mercado de Portugal."""

    @abstractmethod
    def buscar_oportunidades(
        self,
        concelho: Optional[str] = None,
        distrito: Optional[str] = None,
        limite: int = 10,
    ) -> List[Dict[str, Any]]:
        """Busca e retorna uma lista de oportunidades estruturadas."""
        pass

    @abstractmethod
    def extrair_por_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Extrai os dados de um anúncio específico a partir do seu link web."""
        pass

    @staticmethod
    def detectar_tipologia(texto: str) -> str:
        """Identifica a tipologia habitacional padrão portuguesa (T0 a T5+, Moradia, Terreno)."""
        if not texto:
            return "T2"
        t = texto.upper()
        if "MORADIA" in t or "VILLA" in t:
            return "Moradia"
        if "TERRENO" in t or "LOTE" in t:
            return "Terreno"
        if "COMERCIAL" in t or "LOJA" in t:
            return "Loja"

        match = re.search(r"\b(T[0-9](\+[0-9])?)\b", t)
        if match:
            return match.group(1)
        return "T2"

    @staticmethod
    def detectar_regiao_fiscal(distrito: Optional[str], concelho: Optional[str]) -> str:
        """Determina a região fiscal para fins de IMT: continente, madeira ou acores."""
        texto = f"{distrito or ''} {concelho or ''}".lower()
        if any(term in texto for term in ("madeira", "funchal", "porto santo", "santa cruz", "machico")):
            return "madeira"
        if any(term in texto for term in ("açores", "acores", "ponta delgada", "angra", "horta")):
            return "acores"
        return "continente"

    @staticmethod
    def extrair_telemovel_pt(texto: str) -> Optional[str]:
        """Localiza números de telemóvel no padrão de Portugal (91, 92, 93, 96 com 9 dígitos)."""
        if not texto:
            return None
        # Procura +351 9XXXXXXXX ou 9XXXXXXXX
        match = re.search(r"(?:(?:\+|00)351\s*)?([9][1236]\d{7})", texto.replace(" ", "").replace("-", ""))
        if match:
            num = match.group(1)
            return f"+351 {num[0:3]} {num[3:6]} {num[6:9]}"
        return None

    @staticmethod
    def limpar_valor_monetario(valor: Any) -> Decimal:
        """Converte strings com moeda (€) para Decimal seguro."""
        if isinstance(valor, (int, float, Decimal)):
            return Decimal(str(valor))
        if not valor:
            return Decimal("0.00")
        s = str(valor).replace("€", "").replace("EUR", "").strip()
        # Remove pontos de milhares e substitui vírgula decimal
        s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except Exception:
            return Decimal("0.00")
