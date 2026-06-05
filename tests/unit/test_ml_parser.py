"""Testes do parser ML — roda offline contra a golden file.

Golden file: tests/fixtures/ml_ofertas_MLB1051.html
Capturada na validação do ML sem navegador (44+ produtos de celulares).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from luachadinhos.collectors.ml.parser import parsear_html, _extrair_json_hydration

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
GOLDEN_FILE = FIXTURE_DIR / "ml_ofertas_MLB1051.html"


@pytest.fixture(scope="module")
def html_golden() -> str:
    assert GOLDEN_FILE.exists(), f"Golden file não encontrada: {GOLDEN_FILE}"
    return GOLDEN_FILE.read_text(encoding="utf-8")


class TestExtrairJsonHydration:
    def test_encontra_json(self, html_golden):
        data = _extrair_json_hydration(html_golden)
        assert data is not None
        assert "appProps" in data

    def test_items_presentes(self, html_golden):
        data = _extrair_json_hydration(html_golden)
        items = data["appProps"]["pageProps"]["data"]["items"]
        assert len(items) >= 40  # esperamos ~48

    def test_html_sem_json_retorna_none(self):
        assert _extrair_json_hydration("<html><body>nada</body></html>") is None


class TestParsearHtml:
    def test_extrai_produtos(self, html_golden):
        produtos = parsear_html(html_golden, categoria="MLB1051")
        assert len(produtos) >= 40

    def test_campos_basicos_preenchidos(self, html_golden):
        produtos = parsear_html(html_golden, categoria="MLB1051")
        p = produtos[0]
        assert p.plataforma == "mercadolivre"
        assert p.source_id.startswith("MLB")
        assert len(p.titulo) > 5
        assert p.preco_atual > 0
        assert p.url.startswith("https://")
        assert p.categoria == "MLB1051"
        assert p.coletado_em is not None

    def test_preco_original_e_desconto(self, html_golden):
        produtos = parsear_html(html_golden, categoria="MLB1051")
        # Pelo menos alguns devem ter desconto
        com_desconto = [p for p in produtos if p.desconto_pct > 0]
        assert len(com_desconto) >= 10
        for p in com_desconto:
            assert p.preco_original >= p.preco_atual
            assert p.economia >= 0

    def test_avaliacao_presente(self, html_golden):
        produtos = parsear_html(html_golden, categoria="MLB1051")
        com_aval = [p for p in produtos if p.avaliacao is not None]
        assert len(com_aval) >= 10
        for p in com_aval:
            assert 0 <= p.avaliacao <= 5

    def test_imagem_url(self, html_golden):
        produtos = parsear_html(html_golden, categoria="MLB1051")
        com_img = [p for p in produtos if p.imagem]
        assert len(com_img) >= 10
        for p in com_img:
            assert p.imagem.startswith("https://")

    def test_frete_gratis_detectado(self, html_golden):
        produtos = parsear_html(html_golden, categoria="MLB1051")
        com_frete = [p for p in produtos if p.frete_gratis is True]
        assert len(com_frete) >= 5

    def test_primeiro_produto_samsung(self, html_golden):
        """Verifica dados do primeiro card (Samsung Galaxy A36) contra a golden file."""
        produtos = parsear_html(html_golden, categoria="MLB1051")
        p = produtos[0]
        assert "Samsung" in p.titulo or "samsung" in p.titulo.lower()
        assert p.preco_atual == 1619
        assert p.preco_original == 2855
        assert p.desconto_pct == 43
        assert p.avaliacao == 4.9
        assert p.n_avaliacoes == 32387

    def test_html_vazio(self):
        produtos = parsear_html("", categoria="teste")
        assert produtos == []

    def test_nao_confunde_parcela_com_preco(self, html_golden):
        """Armadilha 2 do STATUS.md: preço parcelado != preço à vista."""
        produtos = parsear_html(html_golden, categoria="MLB1051")
        # O primeiro produto tem parcelado = 1799, à vista = 1619
        p = produtos[0]
        assert p.preco_atual == 1619  # PIX/à vista
        assert p.preco_parcelado == 1799  # total parcelado
        assert p.preco_atual < p.preco_parcelado
