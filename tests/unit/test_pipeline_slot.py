"""Testes do pipeline do slot — dry-run sem banco/rede."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.pipeline.slot import executar_slot
from luachadinhos.collectors.ml.fetch import FetchResult

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
GOLDEN_FILE = FIXTURE_DIR / "ml_ofertas_MLB1051.html"


@pytest.fixture
def html_golden() -> str:
    return GOLDEN_FILE.read_text(encoding="utf-8")


class TestExecutarSlot:
    @patch("luachadinhos.collectors.ml.collector.fetch_ofertas")
    def test_dry_run_basico(self, mock_fetch, html_golden):
        mock_fetch.return_value = FetchResult(
            html=html_golden, status_code=200, url="test",
            antibot_detectado=False, sinais_antibot=[],
        )
        selecionados = executar_slot(
            slot="dev",
            categorias_ml=["MLB1051"],
            dry_run=True,
        )
        assert len(selecionados) > 0
        assert len(selecionados) <= 5  # top_por_disparo default
        for p in selecionados:
            assert p.score is not None
            assert p.nicho
            assert p.mensagem_wa

    @patch("luachadinhos.collectors.ml.collector.fetch_ofertas")
    def test_dry_run_diversidade(self, mock_fetch, html_golden):
        mock_fetch.return_value = FetchResult(
            html=html_golden, status_code=200, url="test",
            antibot_detectado=False, sinais_antibot=[],
        )
        from luachadinhos.models.filtros import Filtros
        filtros = Filtros(max_por_nicho=1, top_por_disparo=5)
        selecionados = executar_slot(
            slot="dev",
            categorias_ml=["MLB1051"],
            filtros=filtros,
            dry_run=True,
        )
        # Com max_por_nicho=1, deve ter nichos variados
        nichos = [p.nicho for p in selecionados]
        assert len(set(nichos)) == len(nichos)  # todos diferentes

    @patch("luachadinhos.collectors.ml.collector.fetch_ofertas")
    def test_sem_produtos(self, mock_fetch):
        mock_fetch.return_value = FetchResult(
            html="<html></html>", status_code=200, url="test",
            antibot_detectado=False, sinais_antibot=[],
        )
        selecionados = executar_slot(slot="dev", dry_run=True)
        assert selecionados == []
