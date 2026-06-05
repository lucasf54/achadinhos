"""Firewall PT-BR — tradução entre `Produto` (interno) e o dict de chaves em
português usado pelo Excel, pelas mensagens de WhatsApp e pelo código legado.

Toda a "bagunça" de nomes ('Preço à Vista/PIX', 'Avaliação ⭐', 'Nº Avaliações'
vs 'Vendas'...) fica isolada AQUI. O resto do sistema só conhece `Produto`.

Regras de mapeamento herdadas do legado:
  - ML usa 'Nº Avaliações'; Shopee usa 'Vendas'.
  - ML usa 'Vendedor'; Shopee usa 'Loja'.
"""
from __future__ import annotations

from datetime import datetime

from .produto import Produto

# Mapas de plataforma legível <-> code interno
_PLAT_PARA_DICT = {"mercadolivre": "🛍️ ML", "shopee": "🧡 Shopee"}
_DICT_PARA_PLAT = {
    "🛍️ ML": "mercadolivre", "ML": "mercadolivre", "mercadolivre": "mercadolivre",
    "🧡 Shopee": "shopee", "Shopee": "shopee", "shopee": "shopee",
}


def produto_para_dict(p: Produto) -> dict:
    """Converte um `Produto` interno no dict PT-BR (formato Excel/legado)."""
    plat = _PLAT_PARA_DICT.get(p.plataforma, p.plataforma)
    coletado = p.coletado_em.strftime("%d/%m/%Y %H:%M") if p.coletado_em else ""
    eh_ml = p.plataforma == "mercadolivre"

    return {
        "_plataforma":        plat,
        "Plataforma":         plat,
        "Categoria":          p.categoria,
        "Nicho":              p.nicho,
        "ID":                 p.source_id,
        "Título":             p.titulo,
        "Preço Original":     p.preco_original,
        "Preço à Vista/PIX":  p.preco_atual,
        "Preço Parcelado":    p.preco_parcelado,
        "Desconto (%)":       p.desconto_pct,
        "Economia (R$)":      p.economia,
        "Avaliação ⭐":       "" if p.avaliacao is None else p.avaliacao,
        # ML -> Nº Avaliações; Shopee -> Vendas
        "Nº Avaliações":      p.n_avaliacoes if eh_ml else None,
        "Vendas":             p.vendas if not eh_ml else None,
        "Comissão (%)":       p.comissao_pct,
        "Frete Grátis":       _frete_str(p.frete_gratis),
        # ML -> Vendedor; Shopee -> Loja
        "Vendedor":           p.vendedor if eh_ml else "",
        "Loja":               p.vendedor if not eh_ml else "",
        "URL Original":       p.url,
        "Link Afiliado":      p.link_afiliado,
        "Imagem":             p.imagem,
        "Mensagem WA":        p.mensagem_wa,
        "Coletado em":        coletado,
        # Campos calculados (internos, prefixo __ p/ não colidir)
        "__desconto_real":    p.desconto_real,
        "__economia_real":    p.economia_real,
        "__score":            p.score,
    }


def dict_para_produto(d: dict) -> Produto:
    """Converte um dict PT-BR (legado) num `Produto` interno."""
    plat_raw = d.get("_plataforma") or d.get("Plataforma") or ""
    plataforma = _DICT_PARA_PLAT.get(plat_raw, plat_raw or "mercadolivre")

    return Produto(
        plataforma=plataforma,
        source_id=str(d.get("ID", "")),
        titulo=d.get("Título", ""),
        preco_atual=_num(d.get("Preço à Vista/PIX")),
        preco_original=_num(d.get("Preço Original")),
        preco_parcelado=_num(d.get("Preço Parcelado")),
        desconto_pct=_num(d.get("Desconto (%)")),
        economia=_num(d.get("Economia (R$)")),
        avaliacao=_num_opt(d.get("Avaliação ⭐")),
        n_avaliacoes=_int_opt(d.get("Nº Avaliações")),
        vendas=_int_opt(d.get("Vendas")),
        comissao_pct=_num_opt(d.get("Comissão (%)")),
        frete_gratis=_frete_bool(d.get("Frete Grátis")),
        vendedor=d.get("Vendedor") or d.get("Loja") or "",
        categoria=d.get("Categoria", ""),
        nicho=d.get("Nicho", ""),
        url=d.get("URL Original", ""),
        link_afiliado=d.get("Link Afiliado", ""),
        imagem=d.get("Imagem", ""),
        mensagem_wa=d.get("Mensagem WA", ""),
        coletado_em=_parse_data(d.get("Coletado em")),
    )


# ── helpers de coerção (tolerantes a campos faltando/sujos) ───────────────────
def _to_float(v):
    """Converte texto em float, entendendo formato BR e US.

    'R$ 1.234,56' -> 1234.56 (vírgula = decimal, ponto = milhar)
    '1234.56'     -> 1234.56 (só ponto = decimal)
    Retorna None se não for número.
    """
    if v in (None, "", "—"):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    # Mantém só dígitos, separadores e sinal
    s = "".join(ch for ch in s if ch.isdigit() or ch in ".,-")
    if not s:
        return None
    if "," in s:
        # Vírgula é o decimal; pontos são milhar -> remove pontos, vírgula vira ponto
        s = s.replace(".", "").replace(",", ".")
    # senão: só ponto (ou nada) — já está no formato float
    try:
        return float(s)
    except ValueError:
        return None


def _num(v) -> float:
    r = _to_float(v)
    return 0.0 if r is None else r


def _num_opt(v):
    return _to_float(v)


def _int_opt(v):
    if v in (None, "", "—"):
        return None
    try:
        return int(str(v).replace(".", "").replace(",", ""))
    except (ValueError, TypeError):
        return None


def _frete_str(b) -> str:
    if b is None:
        return "—"
    return "Sim" if b else "Não"


def _frete_bool(s):
    if s in (None, "", "—"):
        return None
    return str(s).strip().lower() in ("sim", "true", "1")


def _parse_data(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return None
