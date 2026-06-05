"""Round-trip do firewall PT-BR: Produto -> dict -> Produto sem perda."""
from __future__ import annotations

from datetime import datetime

import pytest

from luachadinhos.models.produto import Produto
from luachadinhos.models.schema_ptbr import (
    produto_para_dict,
    dict_para_produto,
)


def _ml() -> Produto:
    return Produto(
        plataforma="mercadolivre",
        source_id="MLB123456",
        titulo="Fone Bluetooth XYZ",
        preco_atual=99.90,
        preco_original=199.90,
        desconto_pct=50.0,
        economia=100.0,
        avaliacao=4.7,
        n_avaliacoes=1234,
        comissao_pct=9.5,
        frete_gratis=True,
        vendedor="Loja do João",
        categoria="eletronicos",
        url="https://mercadolivre.com.br/p/MLB123456",
        coletado_em=datetime(2026, 6, 5, 14, 30),
    )


def _shopee() -> Produto:
    return Produto(
        plataforma="shopee",
        source_id="999_888",
        titulo="Vestido Floral",
        preco_atual=49.90,
        preco_original=89.90,
        desconto_pct=44.0,
        economia=40.0,
        avaliacao=4.9,
        vendas=5000,
        comissao_pct=12.0,
        frete_gratis=False,
        vendedor="Moda Store",
        categoria="moda",
    )


@pytest.mark.parametrize("orig", [_ml(), _shopee()], ids=["ml", "shopee"])
def test_roundtrip_preserva_campos(orig):
    d = produto_para_dict(orig)
    volta = dict_para_produto(d)

    assert volta.plataforma == orig.plataforma
    assert volta.source_id == orig.source_id
    assert volta.titulo == orig.titulo
    assert volta.preco_atual == orig.preco_atual
    assert volta.preco_original == orig.preco_original
    assert volta.desconto_pct == orig.desconto_pct
    assert volta.avaliacao == orig.avaliacao
    assert volta.comissao_pct == orig.comissao_pct
    assert volta.frete_gratis == orig.frete_gratis
    assert volta.categoria == orig.categoria
    assert volta.vendedor == orig.vendedor


def test_ml_usa_n_avaliacoes_nao_vendas():
    d = produto_para_dict(_ml())
    assert d["Nº Avaliações"] == 1234
    assert d["Vendas"] is None
    assert d["Vendedor"] == "Loja do João"
    assert d["Loja"] == ""


def test_shopee_usa_vendas_e_loja():
    d = produto_para_dict(_shopee())
    assert d["Vendas"] == 5000
    assert d["Nº Avaliações"] is None
    assert d["Loja"] == "Moda Store"
    assert d["Vendedor"] == ""


def test_plataforma_emoji_no_dict():
    assert produto_para_dict(_ml())["Plataforma"] == "🛍️ ML"
    assert produto_para_dict(_shopee())["Plataforma"] == "🧡 Shopee"


def test_dict_legado_com_campos_sujos_nao_quebra():
    # Simula dado vindo do scraper antigo, com strings e faltando campos.
    legado = {
        "_plataforma": "🛍️ ML",
        "ID": "MLB777",
        "Título": "Produto teste",
        "Preço à Vista/PIX": "1.234,56",   # formato BR com milhar
        "Avaliação ⭐": "4,5",
        "Nº Avaliações": "2.500",
        "Frete Grátis": "Sim",
    }
    p = dict_para_produto(legado)
    assert p.preco_atual == pytest.approx(1234.56)
    assert p.avaliacao == pytest.approx(4.5)
    assert p.n_avaliacoes == 2500
    assert p.frete_gratis is True
