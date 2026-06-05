"""Testes da classificação de nichos."""
from __future__ import annotations

import pytest

from luachadinhos.decision.nichos import classificar_nicho, aplicar_nichos
from luachadinhos.models.produto import Produto


def _p(titulo: str, categoria: str = "") -> Produto:
    return Produto(
        plataforma="mercadolivre", source_id="MLB1",
        titulo=titulo, categoria=categoria,
    )


class TestClassificarNicho:
    def test_celular(self):
        assert classificar_nicho(_p("Celular Samsung Galaxy A36 5g")) == "Celulares"

    def test_fone(self):
        assert classificar_nicho(_p("Fone Bluetooth TWS Pro 5.0")) == "Áudio"

    def test_notebook(self):
        assert classificar_nicho(_p("Notebook Dell Inspiron 15 i5")) == "Informática"

    def test_air_fryer(self):
        assert classificar_nicho(_p("Fritadeira Air Fryer 4.5L")) == "Eletrodomésticos"

    def test_camiseta(self):
        assert classificar_nicho(_p("Camiseta Polo Ralph Lauren")) == "Moda"

    def test_tenis(self):
        assert classificar_nicho(_p("Tênis Nike Air Max")) == "Calçados"

    def test_perfume(self):
        assert classificar_nicho(_p("Perfume Importado 100ml")) == "Beleza"

    def test_pet(self):
        assert classificar_nicho(_p("Ração Premium Cachorro")) == "Pet"

    def test_game(self):
        assert classificar_nicho(_p("Controle Xbox Series Wireless")) == "Games"

    def test_fallback_categoria_ml(self):
        p = _p("Produto Genérico XYZ", categoria="MLB1051")
        assert classificar_nicho(p) == "Celulares"

    def test_fallback_outros(self):
        p = _p("Produto Totalmente Desconhecido", categoria="MLB9999")
        assert classificar_nicho(p) == "Outros"


class TestAplicarNichos:
    def test_aplica_em_lista(self):
        produtos = [
            _p("Celular Samsung"),
            _p("Fone Bluetooth"),
            _p("Notebook Dell"),
        ]
        aplicar_nichos(produtos)
        assert produtos[0].nicho == "Celulares"
        assert produtos[1].nicho == "Áudio"
        assert produtos[2].nicho == "Informática"
