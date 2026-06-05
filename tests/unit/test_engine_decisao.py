"""Testes do engine de decisão (pipeline completo, sem banco)."""
from __future__ import annotations

import pytest

from luachadinhos.decision.engine import decidir, _selecionar_top_n_diverso
from luachadinhos.models.filtros import Filtros
from luachadinhos.models.produto import Produto


def _p(titulo: str, desconto: float = 30, preco: float = 100,
       avaliacao: float = 4.5, n_aval: int = 500,
       comissao: float = 9.5, plataforma: str = "mercadolivre") -> Produto:
    return Produto(
        plataforma=plataforma,
        source_id=titulo[:15].replace(" ", "_"),
        titulo=titulo,
        preco_atual=preco,
        preco_original=preco / (1 - desconto / 100) if desconto > 0 else preco,
        desconto_pct=desconto,
        economia=round(preco / (1 - desconto / 100) - preco, 2) if desconto > 0 else 0,
        avaliacao=avaliacao,
        n_avaliacoes=n_aval,
        comissao_pct=comissao,
    )


class TestDecidirOffline:
    """Testes do pipeline completo sem banco (dry-run/bootstrap)."""

    def test_pipeline_basico(self):
        produtos = [
            _p("Celular Samsung Galaxy A36 5g", desconto=40, preco=1619),
            _p("Fone Bluetooth TWS Pro", desconto=35, preco=49.90),
            _p("Notebook Dell Inspiron 15", desconto=25, preco=3500),
            _p("Camiseta Polo Masculina", desconto=30, preco=59.90),
            _p("Air Fryer Mondial 4.5L", desconto=45, preco=199.90),
            _p("Tênis Nike Air Max 90", desconto=28, preco=399.90),
        ]
        selecionados = decidir(produtos)
        assert len(selecionados) <= 5  # top_por_disparo default
        assert all(p.score is not None for p in selecionados)
        assert all(p.nicho for p in selecionados)
        assert all(p.desconto_real is not None for p in selecionados)

    def test_dedup_remove_similares(self):
        produtos = [
            _p("Fone Bluetooth TWS Pro 5.0 Preto", desconto=35),
            _p("Fone Bluetooth TWS Pro 5.0 Branco", desconto=30),
            _p("Celular Samsung Galaxy A36", desconto=40),
        ]
        selecionados = decidir(produtos)
        # Fones são similares, só 1 deve passar
        titulos = [p.titulo for p in selecionados]
        fones = [t for t in titulos if "Fone" in t]
        assert len(fones) <= 1

    def test_anti_fake_corta_desconto_baixo(self):
        produtos = [
            _p("Produto Bom", desconto=30, preco=200),
            _p("Produto Ruim", desconto=5, preco=200),  # desconto_real será min(5,25)=5 < 15
        ]
        selecionados = decidir(produtos)
        # O produto com desconto baixo não deve passar
        assert all("Ruim" not in p.titulo for p in selecionados)

    def test_diversidade_nicho(self):
        """Máx 2 do mesmo nicho por disparo."""
        produtos = [
            _p("Celular Samsung Galaxy A36", desconto=40, preco=1619),
            _p("Celular Xiaomi Redmi Note 13", desconto=38, preco=1200),
            _p("Celular Motorola Edge 40", desconto=35, preco=1800),
            _p("Fone Bluetooth JBL", desconto=30, preco=200),
            _p("Camiseta Nike Dri-Fit", desconto=25, preco=89.90),
        ]
        filtros = Filtros(max_por_nicho=2, top_por_disparo=5)
        selecionados = decidir(produtos, filtros=filtros)
        # Máx 2 celulares
        celulares = [p for p in selecionados if p.nicho == "Celulares"]
        assert len(celulares) <= 2

    def test_anti_repeticao(self):
        p_cel = _p("Celular Samsung", desconto=40, preco=1619)
        p_fone = _p("Fone Bluetooth", desconto=35, preco=200)
        produtos = [p_cel, p_fone]
        postados = {f"{p_cel.plataforma}:{p_cel.source_id}"}
        selecionados = decidir(produtos, postados_ids=postados)
        assert all("Samsung" not in p.titulo for p in selecionados)

    def test_lista_vazia(self):
        assert decidir([]) == []

    def test_top_n_respeita_limite(self):
        produtos = [_p(f"Produto {i}", desconto=30 + i, preco=100) for i in range(20)]
        filtros = Filtros(top_por_disparo=3)
        selecionados = decidir(produtos, filtros=filtros)
        assert len(selecionados) <= 3

    def test_economia_minima_filtra(self):
        """Produto com economia < R$10 (min_savings_brl) não passa."""
        p = _p("Produto Barato", desconto=30, preco=20)
        # economia = 20/(1-0.30) - 20 = 8.57 < 10
        selecionados = decidir([p])
        assert len(selecionados) == 0


class TestSelecionarTopNDiverso:
    def test_diversidade(self):
        produtos = []
        for i in range(5):
            p = _p(f"Celular {i}", desconto=40 - i)
            p.nicho = "Celulares"
            p.score = 80 - i
            produtos.append(p)
        p_fone = _p("Fone X", desconto=30)
        p_fone.nicho = "Áudio"
        p_fone.score = 70
        produtos.append(p_fone)

        resultado = _selecionar_top_n_diverso(produtos, top_n=5, max_por_nicho=2)
        celulares = [p for p in resultado if p.nicho == "Celulares"]
        assert len(celulares) <= 2
        # Fone deve entrar
        assert any(p.nicho == "Áudio" for p in resultado)
