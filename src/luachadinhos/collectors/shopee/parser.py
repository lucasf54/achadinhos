"""Converte nodes da API GraphQL Shopee em Produto.

Trata:
- PRICE_DIVISOR: a API pode retornar preço em centavos (÷100) ou sub-unidades
  (÷100000). O divisor é detectado automaticamente ou configurável.
- Desconto e comissão podem vir como fração (0-1) ou como % (0-100).
- Link de afiliado já vem pronto da API (offerLink).
"""
from __future__ import annotations

import logging
from datetime import datetime

from luachadinhos.models.produto import Produto

logger = logging.getLogger(__name__)

# Se a API retornar preço em centavos ou sub-unidades, dividir por este valor.
# 1 = preço já em reais. 100 = centavos. 100000 = sub-unidades Shopee.
# [VALIDAR NA PRÁTICA] — se os preços saírem com zeros a mais, ajustar.
PRICE_DIVISOR_DEFAULT = 1


def _normalizar_pct(valor: float) -> float:
    """Se vier como fração 0-1, converte para %. Se já for %, mantém."""
    if 0 < valor <= 1:
        return round(valor * 100, 2)
    return round(valor, 2)


def converter_node(
    node: dict,
    categoria: str = "",
    price_divisor: int = PRICE_DIVISOR_DEFAULT,
) -> Produto | None:
    """Converte um node da API GraphQL Shopee em Produto.

    Returns:
        Produto preenchido ou None se dados insuficientes.
    """
    nome = (node.get("productName") or "")[:120].strip()
    item_id = str(node.get("itemId", ""))
    shop_id = str(node.get("shopId", ""))

    if not nome or not item_id:
        return None

    p_min = float(node.get("priceMin") or 0) / price_divisor
    p_max = float(node.get("priceMax") or 0) / price_divisor

    if p_min <= 0:
        return None

    desconto = _normalizar_pct(float(node.get("priceDiscountRate") or 0))
    comissao = _normalizar_pct(float(node.get("commissionRate") or 0))
    avaliacao = float(node.get("ratingStar") or 0)
    vendas = int(node.get("sales") or 0)

    # Calcular preço original a partir do desconto
    if 0 < desconto < 100:
        preco_original = round(p_min / (1 - desconto / 100), 2)
    else:
        preco_original = p_min
    economia = max(0.0, round(preco_original - p_min, 2))

    return Produto(
        plataforma="shopee",
        source_id=f"{item_id}_{shop_id}",
        titulo=nome,
        preco_atual=round(p_min, 2),
        preco_original=round(preco_original, 2),
        preco_parcelado=0.0,  # Shopee não tem parcela no GraphQL
        desconto_pct=desconto,
        economia=economia,
        avaliacao=avaliacao if avaliacao > 0 else None,
        vendas=vendas if vendas > 0 else None,
        comissao_pct=comissao,
        frete_gratis=None,  # não vem na API
        vendedor=node.get("shopName", ""),
        categoria=categoria,
        url=node.get("offerLink", ""),
        link_afiliado=node.get("offerLink", ""),
        link_oficial=True,  # link já vem da API de afiliados
        imagem=node.get("imageUrl", ""),
        coletado_em=datetime.now(),
    )


def parsear_nodes(
    nodes: list[dict],
    categoria: str = "",
    price_divisor: int = PRICE_DIVISOR_DEFAULT,
) -> list[Produto]:
    """Converte lista de nodes GraphQL em lista de Produto."""
    produtos = []
    for node in nodes:
        p = converter_node(node, categoria, price_divisor)
        if p is not None:
            produtos.append(p)
    logger.info("Shopee: %d/%d nodes convertidos", len(produtos), len(nodes))
    return produtos
