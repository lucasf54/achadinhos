"""Testes do anti-fake (desconto real)."""
from __future__ import annotations

import pytest

from luachadinhos.db.historico import Stats30d
from luachadinhos.decision.anti_fake import calcular_desconto_real, filtrar_anti_fake
from luachadinhos.models.produto import Produto


def _p(preco_atual=100, desconto_pct=30, economia=50) -> Produto:
    return Produto(
        plataforma="mercadolivre", source_id="MLB1",
        titulo="Produto Teste", preco_atual=preco_atual,
        preco_original=preco_atual + economia,
        desconto_pct=desconto_pct, economia=economia,
    )


class TestCalcularDescontoReal:
    def test_com_historico_completo(self):
        p = _p(preco_atual=80)
        stats = Stats30d(product_id=1, media=120.0, minimo=100.0, n_amostras=10)
        calcular_desconto_real(p, stats)
        # ref = 0.6*120 + 0.4*100 = 112
        # desconto_real = (112 - 80) / 112 * 100 = 28.57%
        assert p.desconto_real == pytest.approx(28.57, abs=0.01)
        assert p.economia_real == pytest.approx(32.0, abs=0.01)
        assert p.historico_curto is False
        assert p.is_real_discount is True

    def test_sem_desconto_real(self):
        p = _p(preco_atual=120)
        stats = Stats30d(product_id=1, media=100.0, minimo=90.0, n_amostras=10)
        calcular_desconto_real(p, stats)
        # ref = 0.6*100 + 0.4*90 = 96. preco > ref → desconto_real = 0
        assert p.desconto_real == 0.0
        assert p.is_real_discount is False

    def test_historico_curto_fallback(self):
        p = _p(desconto_pct=40)
        stats = Stats30d(product_id=1, media=150.0, minimo=130.0, n_amostras=3)
        calcular_desconto_real(p, stats, min_amostras=5)
        # Fallback: min(40, 25) = 25
        assert p.desconto_real == 25.0
        assert p.historico_curto is True

    def test_sem_stats(self):
        p = _p(desconto_pct=20)
        calcular_desconto_real(p, stats=None)
        assert p.desconto_real == 20.0  # min(20, 25)
        assert p.historico_curto is True

    def test_fallback_cap_25(self):
        p = _p(desconto_pct=60)
        calcular_desconto_real(p, stats=None)
        assert p.desconto_real == 25.0  # capped at 25


class TestFiltrarAntiFake:
    def test_filtra_abaixo_do_corte(self):
        p1 = _p()
        p1.desconto_real = 20.0
        p1.economia_real = 50.0

        p2 = _p()
        p2.desconto_real = 10.0  # abaixo do min 15%
        p2.economia_real = 50.0

        p3 = _p()
        p3.desconto_real = 20.0
        p3.economia_real = 5.0  # abaixo do min R$10

        resultado = filtrar_anti_fake([p1, p2, p3])
        assert len(resultado) == 1
        assert resultado[0] is p1

    def test_todos_passam(self):
        ps = []
        for i in range(3):
            p = _p()
            p.desconto_real = 30.0
            p.economia_real = 100.0
            ps.append(p)
        assert len(filtrar_anti_fake(ps)) == 3

    def test_nenhum_passa(self):
        p = _p()
        p.desconto_real = 5.0
        p.economia_real = 3.0
        assert len(filtrar_anti_fake([p])) == 0
