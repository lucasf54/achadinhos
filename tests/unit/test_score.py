"""Testes do score 2.0."""
from __future__ import annotations

import pytest

from luachadinhos.decision.score import calcular_score
from luachadinhos.models.produto import Produto


def _p(**kw) -> Produto:
    defaults = dict(
        plataforma="mercadolivre", source_id="MLB1",
        titulo="Produto Teste", preco_atual=100,
        desconto_pct=30, desconto_real=30.0,
        avaliacao=4.5, n_avaliacoes=1000,
        comissao_pct=9.5,
    )
    defaults.update(kw)
    return Produto(**defaults)


class TestCalcularScore:
    def test_retorna_float(self):
        p = _p()
        score = calcular_score(p)
        assert isinstance(score, float)
        assert score > 0
        assert p.score == score

    def test_maior_desconto_maior_score(self):
        p1 = _p(desconto_real=50.0)
        p2 = _p(desconto_real=10.0)
        calcular_score(p1)
        calcular_score(p2)
        assert p1.score > p2.score

    def test_maior_avaliacao_maior_score(self):
        p1 = _p(avaliacao=5.0)
        p2 = _p(avaliacao=3.0)
        calcular_score(p1)
        calcular_score(p2)
        assert p1.score > p2.score

    def test_penalidade_historico_curto(self):
        p1 = _p(historico_curto=False)
        p2 = _p(historico_curto=True)
        s1 = calcular_score(p1)
        s2 = calcular_score(p2)
        assert s2 == pytest.approx(s1 * 0.90, abs=0.01)

    def test_social_ml_vs_shopee(self):
        """n_avaliacoes ML e vendas Shopee devem ter impacto similar."""
        p_ml = _p(n_avaliacoes=5000, vendas=None)
        p_shopee = _p(n_avaliacoes=None, vendas=35000)  # 5000*7 = 35000
        calcular_score(p_ml)
        calcular_score(p_shopee)
        # Devem ser parecidos (max(5000*7, 0) vs max(0, 35000))
        assert abs(p_ml.score - p_shopee.score) < 2.0

    def test_score_usa_desconto_real_se_disponivel(self):
        p = _p(desconto_pct=50, desconto_real=10.0)
        calcular_score(p)
        # desconto_real=10 é baixo, score não deve ser alto por causa do card
        p2 = _p(desconto_pct=10, desconto_real=50.0)
        calcular_score(p2)
        assert p2.score > p.score

    def test_sem_avaliacao(self):
        p = _p(avaliacao=None)
        score = calcular_score(p)
        assert score > 0  # não crashou

    def test_score_range(self):
        # Score máximo teórico: ~100 (todos 100/100)
        p = _p(desconto_real=60.0, avaliacao=5.0, n_avaliacoes=100000,
               comissao_pct=16.0, score_novidade=100.0, historico_curto=False)
        score = calcular_score(p)
        assert 0 < score <= 100
