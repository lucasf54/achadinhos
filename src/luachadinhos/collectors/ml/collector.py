"""MLCollector — orquestrador do coletor ML sem navegador.

Pipeline: fetch HTML → parse JSON hydration → desconto/comissão → link afiliado.
Recebe Filtros e lista de categorias, retorna lista de Produto.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from luachadinhos.models.filtros import Filtros
from luachadinhos.models.produto import Produto

from .afiliado import carregar_cookies, gerar_link_oficial, link_manual, renovar_sessao
from .desconto import aplicar_desconto_economia
from .fetch import fetch_ofertas
from .parser import parsear_html

logger = logging.getLogger(__name__)

# Caminho padrão do arquivo de cookies
_COOKIES_DEFAULT = Path(__file__).resolve().parents[4] / "secrets" / "ml_cookies.json"


class MLCollector:
    """Coleta ofertas do ML para uma ou mais categorias."""

    def __init__(
        self,
        filtros: Filtros | None = None,
        cookies_path: str | Path | None = None,
    ):
        self.filtros = filtros or Filtros()
        self._cookies_path = Path(cookies_path) if cookies_path else _COOKIES_DEFAULT
        self._cookies_str: str = ""
        self._csrf_token: str = ""

    def _carregar_cookies(self) -> None:
        """Carrega e renova cookies de afiliado (se existirem)."""
        if self._cookies_path.exists():
            self._cookies_str = carregar_cookies(self._cookies_path)
            logger.info(
                "Cookies carregados de %s — renovando sessão...",
                self._cookies_path.name,
            )
            self._cookies_str, self._csrf_token = renovar_sessao(self._cookies_str)
            if self._csrf_token:
                logger.info("CSRF token obtido — links oficiais habilitados")
        else:
            logger.warning(
                "Cookies não encontrados em %s — links serão manuais",
                self._cookies_path,
            )

    def _gerar_links(self, produtos: list[Produto]) -> list[Produto]:
        """Gera links de afiliado para todos os produtos."""
        if not self._cookies_str:
            for p in produtos:
                if p.url:
                    p.link_afiliado = link_manual(p.url)
                    p.link_oficial = False
            return produtos

        resultado: list[Produto] = []
        for i, p in enumerate(produtos, 1):
            if not p.url:
                resultado.append(p)
                continue
            link, oficial = gerar_link_oficial(p.url, self._cookies_str, self._csrf_token)
            p.link_afiliado = link
            p.link_oficial = oficial
            if not oficial:
                logger.warning(
                    "[%d/%d] Link oficial falhou: %s",
                    i, len(produtos), p.titulo[:50],
                )
            resultado.append(p)
            time.sleep(0.3)  # throttle p/ não estressar a API

        return resultado

    def coletar(
        self,
        categorias: list[str],
        dry_run: bool = False,
    ) -> list[Produto]:
        """Coleta ofertas de todas as categorias.

        Args:
            categorias: lista de códigos ML (ex: ["MLB1051", "MLB1403"]).
            dry_run: se True, não gera links de afiliado.

        Returns:
            Lista de Produto coletados e enriquecidos.
        """
        if not dry_run:
            self._carregar_cookies()

        todos: list[Produto] = []

        for cat in categorias:
            logger.info("Coletando categoria %s...", cat)
            try:
                result = fetch_ofertas(
                    categoria=cat,
                    preco_max=self.filtros.preco_max,
                )
            except ConnectionError as e:
                logger.error("Falha no fetch de %s: %s", cat, e)
                continue

            if result.status_code != 200:
                logger.warning(
                    "HTTP %d para %s — pode ser bloqueio",
                    result.status_code, cat,
                )

            if result.antibot_detectado:
                logger.warning(
                    "Anti-bot detectado em %s: %s",
                    cat, result.sinais_antibot,
                )
                continue

            produtos = parsear_html(result.html, categoria=cat)
            logger.info("%d produtos parseados de %s", len(produtos), cat)

            for p in produtos:
                aplicar_desconto_economia(p)

            todos.extend(produtos)
            time.sleep(1.5)  # throttle entre categorias

        # Dedup por source_id
        vistos: set[str] = set()
        unicos: list[Produto] = []
        for p in todos:
            if p.source_id not in vistos:
                vistos.add(p.source_id)
                unicos.append(p)
        logger.info(
            "Total: %d produtos únicos (de %d coletados)",
            len(unicos), len(todos),
        )

        if not dry_run:
            unicos = self._gerar_links(unicos)

        return unicos
