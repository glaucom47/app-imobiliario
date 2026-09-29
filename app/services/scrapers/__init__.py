"""
Módulo de Scrapers e Extratores de Fontes Abertas para Captação de Imóveis.
Fontes suportadas:
- e-leiloes.pt (Hasta Pública e Penhoras Judiciais em Portugal)
- OLX Portugal (Anúncios de Particulares / FSBO)
"""
from app.services.scrapers.base_scraper import BaseScraper
from app.services.scrapers.eleiloes_scraper import EleiloesScraper
from app.services.scrapers.olx_scraper import OlxScraper

__all__ = ["BaseScraper", "EleiloesScraper", "OlxScraper"]
