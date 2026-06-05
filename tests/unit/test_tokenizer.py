"""Testes do tokenizer e similaridade Jaccard."""
from __future__ import annotations

import pytest

from luachadinhos.decision.tokenizer import tokenizar, jaccard, garantir_tokens
from luachadinhos.models.produto import Produto


class TestTokenizar:
    def test_basico(self):
        tokens = tokenizar("Fone Bluetooth TWS Pro 5.0")
        assert "fone" in tokens
        assert "bluetooth" in tokens
        assert "tws" in tokens
        assert "pro" in tokens
        # "5" tem 1 char → removido; "0" também
        assert "5.0" not in tokens

    def test_remove_acentos(self):
        tokens = tokenizar("Câmera de Segurança")
        assert "camera" in tokens
        assert "seguranca" in tokens

    def test_remove_stopwords(self):
        tokens = tokenizar("Fone de Ouvido com Bluetooth")
        assert "de" not in tokens
        assert "com" not in tokens
        assert "fone" in tokens
        assert "ouvido" in tokens

    def test_remove_pontuacao(self):
        tokens = tokenizar("Kit 3-em-1 (Preto/Azul)")
        assert "kit" in tokens
        assert "preto" in tokens

    def test_retorna_frozenset(self):
        result = tokenizar("teste")
        assert isinstance(result, frozenset)

    def test_titulo_vazio(self):
        assert tokenizar("") == frozenset()


class TestJaccard:
    def test_identicos(self):
        a = frozenset({"fone", "bluetooth"})
        assert jaccard(a, a) == 1.0

    def test_disjuntos(self):
        a = frozenset({"fone", "bluetooth"})
        b = frozenset({"camiseta", "algodao"})
        assert jaccard(a, b) == 0.0

    def test_parcial(self):
        a = frozenset({"fone", "bluetooth", "tws"})
        b = frozenset({"fone", "bluetooth", "pro"})
        # inter=2, union=4 → 0.5
        assert jaccard(a, b) == 0.5

    def test_vazio(self):
        assert jaccard(frozenset(), frozenset({"a"})) == 0.0
        assert jaccard(frozenset(), frozenset()) == 0.0


class TestGarantirTokens:
    def test_cacheia(self):
        p = Produto(plataforma="ml", source_id="1", titulo="Fone Bluetooth")
        t1 = garantir_tokens(p)
        t2 = garantir_tokens(p)
        assert t1 is t2  # mesmo objeto (cacheado)
        assert "fone" in t1
