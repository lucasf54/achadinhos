"""Testes de deduplicação por similaridade."""
from __future__ import annotations

import pytest

from luachadinhos.decision.dedup import dedup_similares
from luachadinhos.models.produto import Produto


def _p(titulo: str, desconto: float = 20) -> Produto:
    return Produto(
        plataforma="mercadolivre", source_id=titulo[:10],
        titulo=titulo, desconto_pct=desconto,
    )


class TestDedupSimilares:
    def test_mantem_unicos(self):
        produtos = [
            _p("Fone Bluetooth TWS Pro 5.0", desconto=30),
            _p("Camiseta Algodão Masculina", desconto=25),
        ]
        resultado = dedup_similares(produtos, threshold=0.55)
        assert len(resultado) == 2

    def test_remove_similar(self):
        produtos = [
            _p("Fone Bluetooth TWS Pro 5.0 Preto", desconto=30),
            _p("Fone Bluetooth TWS Pro 5.0 Branco", desconto=25),
        ]
        resultado = dedup_similares(produtos, threshold=0.55)
        assert len(resultado) == 1
        # Mantém o de maior desconto
        assert resultado[0].desconto_pct == 30

    def test_cross_plataforma(self):
        p1 = Produto(
            plataforma="mercadolivre", source_id="MLB123",
            titulo="Fone Bluetooth TWS Pro 5.0", desconto_pct=30,
        )
        p2 = Produto(
            plataforma="shopee", source_id="123_456",
            titulo="Fone Bluetooth TWS Pro 5.0", desconto_pct=35,
        )
        resultado = dedup_similares([p1, p2], threshold=0.55)
        assert len(resultado) == 1
        # Shopee tem mais desconto
        assert resultado[0].plataforma == "shopee"

    def test_threshold_alto_mantem_mais(self):
        produtos = [
            _p("Fone Bluetooth TWS Pro 5.0 Preto", desconto=30),
            _p("Fone Bluetooth TWS Pro 5.0 Branco", desconto=25),
        ]
        resultado = dedup_similares(produtos, threshold=0.95)
        assert len(resultado) == 2  # threshold alto = mais permissivo

    def test_lista_vazia(self):
        assert dedup_similares([], threshold=0.55) == []
