"""Testes do ShopeeCollector — sem rede (mockado)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from luachadinhos.collectors.shopee.collector import ShopeeCollector

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_FILE = FIXTURE_DIR / "shopee_response_sample.json"


@pytest.fixture
def nodes() -> list[dict]:
    data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    return data["data"]["productOfferV2"]["nodes"]


class TestShopeeCollector:
    @patch.dict("os.environ", {"SHOPEE_APP_ID": "", "SHOPEE_SECRET": ""})
    def test_sem_credenciais_retorna_vazio(self):
        collector = ShopeeCollector(app_id="", secret="")
        produtos = collector.coletar(["fone bluetooth"])
        assert produtos == []

    @patch("luachadinhos.collectors.shopee.collector.buscar_por_keyword")
    def test_coleta_com_mock(self, mock_buscar, nodes):
        mock_buscar.return_value = nodes
        collector = ShopeeCollector(app_id="test", secret="test")
        produtos = collector.coletar(["fone bluetooth"], categorias=["fones"])

        assert len(produtos) == 3  # 4 nodes - 1 inválido
        assert all(p.plataforma == "shopee" for p in produtos)
        assert all(p.categoria == "fones" for p in produtos)

    @patch("luachadinhos.collectors.shopee.collector.buscar_por_keyword")
    def test_dedup_source_id(self, mock_buscar, nodes):
        """Mesma keyword 2x → dedup por source_id."""
        mock_buscar.return_value = nodes
        collector = ShopeeCollector(app_id="test", secret="test")
        produtos = collector.coletar(
            ["fone bluetooth", "fone bluetooth"],
            categorias=["fones", "fones"],
        )
        ids = [p.source_id for p in produtos]
        assert len(ids) == len(set(ids))

    @patch("luachadinhos.collectors.shopee.collector.buscar_por_keyword")
    def test_erro_api_nao_quebra(self, mock_buscar):
        mock_buscar.side_effect = ConnectionError("timeout")
        collector = ShopeeCollector(app_id="test", secret="test")
        produtos = collector.coletar(["fone"])
        assert produtos == []

    @patch("luachadinhos.collectors.shopee.collector.buscar_por_keyword")
    def test_keyword_como_categoria_default(self, mock_buscar, nodes):
        mock_buscar.return_value = nodes
        collector = ShopeeCollector(app_id="test", secret="test")
        produtos = collector.coletar(["fone bluetooth"])
        # Sem categorias explícitas, usa keyword como rótulo
        assert produtos[0].categoria == "fone bluetooth"
