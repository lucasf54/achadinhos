"""Testes do módulo de desconto/economia/comissão ML."""
from __future__ import annotations

import pytest

from luachadinhos.collectors.ml.desconto import (
    aplicar_desconto_economia,
    calcular_comissao,
)
from luachadinhos.models.produto import Produto


def _produto(**kw) -> Produto:
    defaults = dict(plataforma="mercadolivre", source_id="MLB123", titulo="Teste")
    defaults.update(kw)
    return Produto(**defaults)


class TestCalcularComissao:
    def test_celular(self):
        assert calcular_comissao("Celular Samsung Galaxy") == 5.0

    def test_perfume(self):
        assert calcular_comissao("Perfume Importado") == 16.0

    def test_fone(self):
        assert calcular_comissao("Fone Bluetooth TWS") == 9.5

    def test_default(self):
        assert calcular_comissao("Produto Genérico XYZ") == 9.5

    def test_usa_categoria(self):
        assert calcular_comissao("Produto X", categoria="beleza") == 16.0


class TestAplicarDescontoEconomia:
    def test_recalcula_original_sem_preco(self):
        p = _produto(preco_atual=80, preco_original=0, desconto_pct=20)
        aplicar_desconto_economia(p)
        assert p.preco_original == 100.0
        assert p.economia == 20.0

    def test_recalcula_desconto_sem_pct(self):
        p = _produto(preco_atual=80, preco_original=100, desconto_pct=0)
        aplicar_desconto_economia(p)
        assert p.desconto_pct == 20.0

    def test_economia_nunca_negativa(self):
        p = _produto(preco_atual=100, preco_original=90, desconto_pct=0)
        aplicar_desconto_economia(p)
        assert p.economia == 0
        # original corrigido para >= atual
        assert p.preco_original == 100

    def test_comissao_atribuida(self):
        p = _produto(titulo="Celular Samsung", preco_atual=1000, preco_original=1500)
        aplicar_desconto_economia(p)
        assert p.comissao_pct == 5.0

    def test_original_zero_sem_desconto(self):
        p = _produto(preco_atual=50, preco_original=0, desconto_pct=0)
        aplicar_desconto_economia(p)
        assert p.preco_original == 50
        assert p.economia == 0
