"""ShopeeCollector — orquestrador do coletor Shopee via API GraphQL.

Pipeline: busca por keyword → converte nodes → Produto.
Link de afiliado já vem da API (offerLink), sem etapa extra.
"""
from __future__ import annotations

import logging
import os
import time

from luachadinhos.models.filtros import Filtros
from luachadinhos.models.produto import Produto

from .api import buscar_por_keyword
from .parser import parsear_nodes, PRICE_DIVISOR_DEFAULT

logger = logging.getLogger(__name__)


def _cred(env_key: str, settings_attr: str) -> str:
    """Lê credencial via get_settings() (com .env carregado); fallback os.getenv."""
    try:
        from luachadinhos.config.settings import get_settings
        return getattr(get_settings(), settings_attr, "") or os.getenv(env_key, "")
    except Exception:
        return os.getenv(env_key, "")


class ShopeeCollector:
    """Coleta ofertas da Shopee para uma ou mais keywords."""

    def __init__(
        self,
        filtros: Filtros | None = None,
        app_id: str = "",
        secret: str = "",
        price_divisor: int = PRICE_DIVISOR_DEFAULT,
        limite_por_keyword: int = 30,
    ):
        self.filtros = filtros or Filtros()
        # Lê via get_settings() (garante .env carregado); fallback p/ os.getenv.
        # Ler só com os.getenv no import pegava vazio quando o .env ainda não
        # tinha sido carregado (mesmo bug que afetou o MATT_WORD do ML).
        self.app_id = app_id or _cred("SHOPEE_APP_ID", "shopee_app_id")
        self.secret = secret or _cred("SHOPEE_SECRET", "shopee_secret")
        self.price_divisor = price_divisor
        self.limite_por_keyword = limite_por_keyword

    def coletar(
        self,
        keywords: list[str],
        categorias: list[str] | None = None,
    ) -> list[Produto]:
        """Coleta ofertas para todas as keywords.

        Args:
            keywords: lista de termos de busca (ex: ["fone bluetooth", "air fryer"]).
            categorias: rótulos de categoria, 1:1 com keywords (opcional).
                       Se omitido, usa a keyword como rótulo.

        Returns:
            Lista de Produto coletados e enriquecidos.
        """
        if not self.app_id or not self.secret:
            logger.error(
                "SHOPEE_APP_ID e SHOPEE_SECRET não configurados. "
                "Defina no .env ou passe ao construtor."
            )
            return []

        if categorias is None:
            categorias = keywords

        if len(categorias) != len(keywords):
            categorias = keywords

        todos: list[Produto] = []

        for keyword, cat in zip(keywords, categorias):
            logger.info("Shopee: buscando '%s' (categoria: %s)...", keyword, cat)
            try:
                nodes = buscar_por_keyword(
                    keyword=keyword,
                    app_id=self.app_id,
                    secret=self.secret,
                    limite=self.limite_por_keyword,
                )
            except (ConnectionError, ValueError) as e:
                logger.error("Falha na busca '%s': %s", keyword, e)
                continue

            produtos = parsear_nodes(nodes, categoria=cat, price_divisor=self.price_divisor)
            logger.info("%d produtos de '%s'", len(produtos), keyword)
            todos.extend(produtos)
            time.sleep(0.5)  # throttle entre keywords

        # Dedup por source_id
        vistos: set[str] = set()
        unicos: list[Produto] = []
        for p in todos:
            if p.source_id not in vistos:
                vistos.add(p.source_id)
                unicos.append(p)

        logger.info(
            "Shopee total: %d produtos únicos (de %d coletados)",
            len(unicos), len(todos),
        )
        return unicos
