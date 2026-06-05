"""Testes do parser Shopee — offline com fixture JSON."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from luachadinhos.collectors.shopee.parser import converter_node, parsear_nodes

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_FILE = FIXTURE_DIR / "shopee_response_sample.json"


@pytest.fixture(scope="module")
def nodes() -> list[dict]:
    data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    return data["data"]["productOfferV2"]["nodes"]


class TestConverterNode:
    def test_node_completo(self, nodes):
        p = converter_node(nodes[0], categoria="fones")
        assert p is not None
        assert p.plataforma == "shopee"
        assert p.source_id == "12345678_87654321"
        assert p.titulo == "Fone Bluetooth TWS Pro 5.0 com Cancelamento de Ruído"
        assert p.preco_atual == 49.90
        assert p.desconto_pct == 35
        assert p.comissao_pct == 12.5
        assert p.avaliacao == 4.7
        assert p.vendas == 15230
        assert p.vendedor == "TechStore Oficial"
        assert p.link_afiliado == "https://shope.ee/abc123_affiliate"
        assert p.link_oficial is True
        assert p.categoria == "fones"

    def test_desconto_como_fracao(self, nodes):
        """priceDiscountRate=0.40 deve virar 40%."""
        p = converter_node(nodes[1])
        assert p is not None
        assert p.desconto_pct == 40.0

    def test_comissao_como_fracao(self, nodes):
        """commissionRate=0.10 deve virar 10%."""
        p = converter_node(nodes[1])
        assert p.comissao_pct == 10.0

    def test_preco_original_calculado(self, nodes):
        p = converter_node(nodes[0])
        # 49.90 / (1 - 35/100) = 76.77
        assert p.preco_original == pytest.approx(76.77, abs=0.01)
        assert p.economia == pytest.approx(26.87, abs=0.01)

    def test_sem_desconto(self, nodes):
        p = converter_node(nodes[2])
        assert p is not None
        assert p.desconto_pct == 0
        assert p.preco_original == p.preco_atual
        assert p.economia == 0

    def test_node_invalido_retorna_none(self, nodes):
        """Node com dados vazios deve ser ignorado."""
        p = converter_node(nodes[3])
        assert p is None

    def test_sem_avaliacao(self, nodes):
        p = converter_node(nodes[2])
        assert p.avaliacao is None  # ratingStar=0 → None
        assert p.vendas is None  # sales=0 → None

    def test_price_divisor(self, nodes):
        """Com divisor 100, preço deve ser dividido."""
        node = dict(nodes[0])
        node["priceMin"] = 4990  # centavos
        node["priceMax"] = 8990
        p = converter_node(node, price_divisor=100)
        assert p.preco_atual == 49.90


class TestParsearNodes:
    def test_filtra_invalidos(self, nodes):
        produtos = parsear_nodes(nodes, categoria="fones")
        # 4 nodes, mas o último é inválido
        assert len(produtos) == 3

    def test_categoria_propagada(self, nodes):
        produtos = parsear_nodes(nodes, categoria="audio")
        for p in produtos:
            assert p.categoria == "audio"
