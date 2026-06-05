"""Anti-fake — calcula desconto REAL com base no histórico de preço.

Fórmula do plano:
    ref           = 0.6 * media_30d + 0.4 * min_30d
    desconto_real = max(0, (ref - preco_hoje) / ref * 100)

Histórico curto (< min_amostras): fallback min(desconto_card, 25) e
penaliza score via flag historico_curto.

Bootstrap: funciona desde o dia 1 (fallback), fica mais honesto
conforme o histórico enche (~30 dias).
"""
from __future__ import annotations

import logging

from luachadinhos.db.historico import Stats30d
from luachadinhos.models.produto import Produto

logger = logging.getLogger(__name__)

# Teto do fallback para histórico curto
_FALLBACK_CAP = 25.0


def calcular_desconto_real(
    produto: Produto,
    stats: Stats30d | None,
    min_amostras: int = 5,
) -> None:
    """Calcula desconto_real e economia_real no produto (in-place).

    Se stats é None ou n_amostras < min_amostras → fallback.
    """
    if stats is None or stats.n_amostras < min_amostras:
        # Histórico curto: fallback conservador
        produto.desconto_real = min(produto.desconto_pct, _FALLBACK_CAP)
        produto.economia_real = produto.economia
        produto.historico_curto = True
        produto.avg_price_30d = None
        produto.is_real_discount = None
        return

    ref = 0.6 * stats.media + 0.4 * stats.minimo
    produto.avg_price_30d = round(ref, 2)
    produto.historico_curto = False

    if ref <= 0:
        produto.desconto_real = 0.0
        produto.economia_real = 0.0
        produto.is_real_discount = False
        return

    desconto_real = max(0.0, (ref - produto.preco_atual) / ref * 100)
    economia_real = max(0.0, ref - produto.preco_atual)

    produto.desconto_real = round(desconto_real, 2)
    produto.economia_real = round(economia_real, 2)
    produto.is_real_discount = desconto_real > 0


def filtrar_anti_fake(
    produtos: list[Produto],
    desconto_real_min: float = 15.0,
    min_savings_brl: float = 10.0,
) -> list[Produto]:
    """Filtra produtos que não passam no corte de desconto real.

    Precisa que calcular_desconto_real já tenha sido chamado.
    """
    resultado = []
    for p in produtos:
        dr = p.desconto_real if p.desconto_real is not None else 0
        er = p.economia_real if p.economia_real is not None else 0
        if dr >= desconto_real_min and er >= min_savings_brl:
            resultado.append(p)

    logger.info(
        "Anti-fake: %d → %d (min_desc=%.0f%%, min_sav=R$%.0f)",
        len(produtos), len(resultado), desconto_real_min, min_savings_brl,
    )
    return resultado
