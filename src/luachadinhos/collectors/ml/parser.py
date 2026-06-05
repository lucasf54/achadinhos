"""Parser de hydration do ML — extrai produtos do JSON embutido no HTML.

A página /ofertas do ML embute os dados dos cards num JSON de hydration
no formato ``_n.ctx.r = { ... }``. Os produtos ficam em:
    appProps.pageProps.data.items[*].card

Cada card tem uma lista de ``components`` tipados (title, price, reviews,
shipping, seller, etc.) no formato "polycard".

Armadilhas tratadas (documentadas no STATUS.md):
1. Preço de parcela confundido com preço à vista — distinguimos
   current_price (PIX/à vista) de installments.price_total.
2. Campos opcionais (reviews, seller, shipping) podem faltar.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from luachadinhos.models.produto import Produto

logger = logging.getLogger(__name__)

# Regex para extrair o JSON de hydration (_n.ctx.r={...})
_RE_HYDRATION = re.compile(r"_n\.ctx\.r\s*=\s*(\{)", re.DOTALL)


def _extrair_json_hydration(html: str) -> dict | None:
    """Acha o maior bloco _n.ctx.r={...} no HTML e faz parse."""
    melhor: dict | None = None
    melhor_tam = 0

    for m in _RE_HYDRATION.finditer(html):
        start = m.start(1)
        depth = 0
        end = start
        for i in range(start, len(html)):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
            if depth == 0:
                end = i + 1
                break

        json_str = html[start:end]
        if len(json_str) <= melhor_tam:
            continue

        try:
            data = json.loads(json_str)
            melhor = data
            melhor_tam = len(json_str)
        except json.JSONDecodeError:
            logger.debug("JSON inválido em _n.ctx.r (pos %d, %d chars)", start, len(json_str))

    return melhor


def _comp(components: list[dict], tipo: str) -> dict:
    """Retorna o primeiro componente do tipo dado, ou {} se não existir."""
    for c in components:
        if c.get("type") == tipo:
            return c.get(tipo, {})
    return {}


def _extrair_id(url: str) -> str:
    """Extrai o ID MLB do URL ou metadata."""
    m = re.search(r"MLB-?(\d+)", url, re.IGNORECASE)
    return f"MLB{m.group(1)}" if m else ""


def _extrair_vendedor(seller: dict) -> str:
    """Extrai nome do vendedor do componente seller."""
    texto = seller.get("text", "")
    # Remove templates tipo {icon_cockade}
    texto = re.sub(r"\{[^}]+\}", "", texto).strip()
    # Remove "Por " inicial
    texto = re.sub(r"^[Pp]or\s+", "", texto).strip()
    return texto


def _imagem_url(pictures: dict) -> str:
    """Monta URL da imagem a partir do ID."""
    pics = pictures.get("pictures", [])
    if not pics:
        return ""
    pic_id = pics[0].get("id", "")
    if not pic_id:
        return ""
    return f"https://http2.mlstatic.com/D_{pic_id}-O.jpg"


def parsear_html(html: str, categoria: str = "") -> list[Produto]:
    """Parseia o HTML de /ofertas e retorna lista de Produtos.

    Args:
        html: HTML completo da página /ofertas.
        categoria: rótulo da categoria (ex: "MLB1051" ou "celulares").

    Returns:
        Lista de Produto com campos preenchidos pelo parser.
    """
    data = _extrair_json_hydration(html)
    if data is None:
        logger.error("JSON de hydration não encontrado no HTML")
        return []

    items = (
        data
        .get("appProps", {})
        .get("pageProps", {})
        .get("data", {})
        .get("items", [])
    )

    if not items:
        logger.warning("Nenhum item encontrado no JSON de hydration")
        return []

    produtos: list[Produto] = []
    agora = datetime.now()

    for item in items:
        try:
            card = item.get("card", {})
            meta = card.get("metadata", {})
            comps = card.get("components", [])

            # Título
            title_comp = _comp(comps, "title")
            titulo = title_comp.get("text", "")
            if not titulo:
                continue

            # URL
            url_base = meta.get("url", "")
            if url_base and not url_base.startswith("http"):
                url_base = "https://" + url_base

            # ID
            source_id = meta.get("product_id") or meta.get("id") or _extrair_id(url_base)
            if not source_id:
                continue

            # Preço
            price_comp = _comp(comps, "price")
            current = price_comp.get("current_price", {})
            previous = price_comp.get("previous_price", {})

            preco_atual = current.get("value", 0)
            preco_original = previous.get("value", 0)

            if not preco_atual or preco_atual <= 0:
                continue

            # Preço parcelado (total, não da parcela)
            preco_parcelado = 0.0
            installments = price_comp.get("installments", {})
            for v in installments.get("values", []):
                if v.get("key") == "price_total":
                    preco_parcelado = v.get("price", {}).get("value", 0)
                    break

            # Desconto do card
            desconto_pct = 0.0
            discount_label = price_comp.get("discount_label", {}).get("text", "")
            if discount_label:
                m = re.search(r"(\d+)%", discount_label)
                if m:
                    desconto_pct = float(m.group(1))

            # Recalcular desconto se falta ou ajustar preço original (lógica do legado)
            if preco_original <= 0 and desconto_pct > 0:
                preco_original = round(preco_atual / (1 - desconto_pct / 100), 2)
            elif preco_original <= 0:
                preco_original = preco_atual
            if preco_original < preco_atual:
                preco_original = preco_atual
            if preco_original > preco_atual and desconto_pct == 0:
                desconto_pct = round((1 - preco_atual / preco_original) * 100, 1)

            economia = max(round(preco_original - preco_atual, 2), 0)

            # Avaliação
            reviews_comp = _comp(comps, "reviews")
            avaliacao = reviews_comp.get("rating_average")
            n_avaliacoes = reviews_comp.get("total")

            # Frete
            shipping_comp = _comp(comps, "shipping")
            shipping_text = shipping_comp.get("text", "")
            frete_gratis = "gr" in shipping_text.lower() if shipping_text else None

            # Vendedor
            seller_comp = _comp(comps, "seller")
            vendedor = _extrair_vendedor(seller_comp)

            # Imagem
            imagem = _imagem_url(card.get("pictures", {}))

            produtos.append(Produto(
                plataforma="mercadolivre",
                source_id=source_id,
                titulo=titulo[:120],
                preco_atual=float(preco_atual),
                preco_original=float(preco_original),
                preco_parcelado=float(preco_parcelado) if preco_parcelado else 0.0,
                desconto_pct=desconto_pct,
                economia=economia,
                avaliacao=float(avaliacao) if avaliacao is not None else None,
                n_avaliacoes=int(n_avaliacoes) if n_avaliacoes is not None else None,
                frete_gratis=frete_gratis,
                vendedor=vendedor,
                categoria=categoria,
                url=url_base,
                imagem=imagem,
                coletado_em=agora,
            ))

        except Exception:
            logger.debug("Erro ao parsear card", exc_info=True)
            continue

    logger.info("Parseados %d produtos de %d items", len(produtos), len(items))
    return produtos
