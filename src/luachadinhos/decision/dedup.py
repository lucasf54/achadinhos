"""Deduplicação cross-plataforma por similaridade de título.

Remove produtos com títulos muito parecidos (Jaccard >= threshold).
Entre similares, mantém o de maior desconto. Funciona cross ML↔Shopee.
"""
from __future__ import annotations

import logging

from luachadinhos.models.produto import Produto

from .tokenizer import garantir_tokens, jaccard

logger = logging.getLogger(__name__)


def dedup_similares(
    produtos: list[Produto],
    threshold: float = 0.55,
) -> list[Produto]:
    """Remove produtos com títulos similares, mantendo o de maior desconto.

    Ordena por desconto decrescente e percorre: se o título de um candidato
    tem Jaccard >= threshold com algum já aceito, descarta.

    Args:
        produtos: lista de Produto (pode misturar plataformas).
        threshold: Jaccard mínimo para considerar "mesmo produto".

    Returns:
        Lista filtrada (sem duplicatas por similaridade).
    """
    ordenados = sorted(produtos, key=lambda p: p.desconto_pct, reverse=True)

    aceitos: list[Produto] = []
    tokens_aceitos: list[frozenset[str]] = []

    for p in ordenados:
        tokens_p = garantir_tokens(p)
        similar = False
        for tokens_a in tokens_aceitos:
            if jaccard(tokens_p, tokens_a) >= threshold:
                similar = True
                break
        if not similar:
            aceitos.append(p)
            tokens_aceitos.append(tokens_p)

    logger.info("Dedup: %d → %d (threshold=%.2f)", len(produtos), len(aceitos), threshold)
    return aceitos
