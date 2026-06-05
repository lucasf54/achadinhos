"""Testes do MLCollector integrado — sem rede (mockado)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.collectors.ml.collector import MLCollector
from luachadinhos.collectors.ml.fetch import FetchResult
from luachadinhos.models.filtros import Filtros

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
GOLDEN_FILE = FIXTURE_DIR / "ml_ofertas_MLB1051.html"


@pytest.fixture
def html_golden() -> str:
    return GOLDEN_FILE.read_text(encoding="utf-8")


class TestMLCollector:
    @patch("luachadinhos.collectors.ml.collector.fetch_ofertas")
    def test_coleta_dry_run(self, mock_fetch, html_golden):
        mock_fetch.return_value = FetchResult(
            html=html_golden,
            status_code=200,
            url="https://www.mercadolivre.com.br/ofertas?category=MLB1051",
            antibot_detectado=False,
            sinais_antibot=[],
        )
        collector = MLCollector()
        produtos = collector.coletar(["MLB1051"], dry_run=True)

        assert len(produtos) >= 40
        # dry_run não chama cookies
        assert collector._cookies_str == ""
        # Verifica desconto/comissão foram aplicados
        for p in produtos:
            assert p.comissao_pct is not None

    @patch("luachadinhos.collectors.ml.collector.fetch_ofertas")
    def test_dedup_por_source_id(self, mock_fetch, html_golden):
        """Se a mesma categoria vier duplicada, dedup remove."""
        mock_fetch.return_value = FetchResult(
            html=html_golden,
            status_code=200,
            url="test",
            antibot_detectado=False,
            sinais_antibot=[],
        )
        collector = MLCollector()
        # Mesma categoria 2x → dedup deve manter os mesmos
        produtos = collector.coletar(["MLB1051", "MLB1051"], dry_run=True)
        ids = [p.source_id for p in produtos]
        assert len(ids) == len(set(ids))

    @patch("luachadinhos.collectors.ml.collector.fetch_ofertas")
    def test_pula_antibot(self, mock_fetch):
        mock_fetch.return_value = FetchResult(
            html="<html>captcha</html>",
            status_code=200,
            url="test",
            antibot_detectado=True,
            sinais_antibot=["captcha"],
        )
        collector = MLCollector()
        produtos = collector.coletar(["MLB1051"], dry_run=True)
        assert len(produtos) == 0

    @patch("luachadinhos.collectors.ml.collector.fetch_ofertas")
    def test_erro_conexao_nao_quebra(self, mock_fetch):
        mock_fetch.side_effect = ConnectionError("timeout")
        collector = MLCollector()
        produtos = collector.coletar(["MLB1051"], dry_run=True)
        assert len(produtos) == 0
