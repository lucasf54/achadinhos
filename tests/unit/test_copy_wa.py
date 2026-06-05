"""Testes da geração de mensagem WhatsApp."""
from __future__ import annotations

import pytest

from luachadinhos.publishers.copy import (
    gerar_mensagem_wa,
    gerar_mensagens_batch,
    _hook_criativo,
    _fmt_preco,
)
from luachadinhos.models.produto import Produto


def _p(**kw) -> Produto:
    defaults = dict(
        plataforma="mercadolivre", source_id="MLB123",
        titulo="Fone Bluetooth TWS Pro 5.0",
        preco_atual=99.90, preco_original=149.90,
        preco_parcelado=119.90,
        desconto_pct=33, economia=50.0,
        avaliacao=4.7, n_avaliacoes=1200,
        frete_gratis=True,
        link_afiliado="https://meli.la/abc123",
    )
    defaults.update(kw)
    return Produto(**defaults)


class TestFmtPreco:
    def test_formato_br(self):
        assert _fmt_preco(1234.56) == "R$ 1.234,56"

    def test_preco_baixo(self):
        assert _fmt_preco(9.90) == "R$ 9,90"

    def test_zero(self):
        assert _fmt_preco(0) == "R$ 0,00"


class TestHookCriativo:
    def test_fone(self):
        hook = _hook_criativo("Fone Bluetooth TWS", 30)
        assert hook  # não vazio
        assert "[QUENTE]" in hook  # 30% >= 30

    def test_celular(self):
        hook = _hook_criativo("Celular Samsung Galaxy", 50)
        assert "[IMPERDIVEL]" in hook

    def test_fallback(self):
        hook = _hook_criativo("Produto Genérico Raro", 10)
        assert "OFERTA" in hook


class TestGerarMensagemWa:
    def test_contem_titulo(self):
        msg = gerar_mensagem_wa(_p())
        assert "Fone Bluetooth" in msg

    def test_contem_precos(self):
        msg = gerar_mensagem_wa(_p())
        assert "149,90" in msg  # original
        assert "99,90" in msg  # atual

    def test_contem_link(self):
        msg = gerar_mensagem_wa(_p())
        assert "meli.la" in msg

    def test_contem_frete_gratis(self):
        msg = gerar_mensagem_wa(_p())
        assert "Frete GRATIS" in msg

    def test_contem_avaliacao(self):
        msg = gerar_mensagem_wa(_p())
        assert "4.7" in msg

    def test_contem_plataforma(self):
        msg = gerar_mensagem_wa(_p())
        assert "Mercado Livre" in msg

    def test_shopee(self):
        msg = gerar_mensagem_wa(_p(plataforma="shopee"))
        assert "Shopee" in msg

    def test_sem_desconto(self):
        msg = gerar_mensagem_wa(_p(desconto_pct=0, preco_original=99.90))
        assert "99,90" in msg

    def test_sem_frete(self):
        msg = gerar_mensagem_wa(_p(frete_gratis=False))
        assert "Frete GRATIS" not in msg


class TestGerarMensagensBatch:
    def test_atribui_mensagem(self):
        produtos = [_p(), _p(source_id="MLB456")]
        gerar_mensagens_batch(produtos)
        for p in produtos:
            assert p.mensagem_wa
            assert len(p.mensagem_wa) > 50
