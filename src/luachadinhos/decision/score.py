"""Score 2.0 — ranking composto de sub-scores ponderados.

Fórmula do plano:
    0.30*desconto_real + 0.22*avaliacao + 0.20*social + 0.13*comissao + 0.15*novidade

Sub-scores normalizados 0-100:
    desconto_real: min(desconto_real, 60) / 60 * 100
    avaliacao:     (rating / 5) * 100
    social:        log-scaled, max(n_aval*7, vendas), cap 100k
    comissao:      min(comissao_pct, 16) / 16 * 100
    novidade:      100 se first_seen recente, decai com dias

Penalidade: *0.90 se histórico curto.
"""
from __future__ import annotations

import math

from luachadinhos.models.produto import Produto

# Pesos do plano
W_DESCONTO = 0.30
W_AVALIACAO = 0.22
W_SOCIAL = 0.20
W_COMISSAO = 0.13
W_NOVIDADE = 0.15

# Caps de normalização
_DESCONTO_CAP = 60.0
_COMISSAO_CAP = 16.0
_SOCIAL_LOG_CAP = 5.0  # log10(100_000) = 5

# Penalidade para histórico curto
_PENALIDADE_HISTORICO_CURTO = 0.90


def _sub_desconto(produto: Produto) -> float:
    dr = produto.desconto_real if produto.desconto_real is not None else produto.desconto_pct
    return min(dr, _DESCONTO_CAP) / _DESCONTO_CAP * 100


def _sub_avaliacao(produto: Produto) -> float:
    rating = produto.avaliacao or 0
    return (rating / 5.0) * 100


def _sub_social(produto: Produto) -> float:
    """Social: equaliza ML (n_avaliações) e Shopee (vendas) via max(n_aval*7, vendas)."""
    n_aval = produto.n_avaliacoes or 0
    vendas = produto.vendas or 0
    social_raw = max(n_aval * 7, vendas)
    if social_raw <= 0:
        return 0.0
    return min(math.log10(social_raw) / _SOCIAL_LOG_CAP, 1.0) * 100


def _sub_comissao(produto: Produto) -> float:
    comissao = produto.comissao_pct or 0
    return min(comissao, _COMISSAO_CAP) / _COMISSAO_CAP * 100


def _sub_novidade(produto: Produto) -> float:
    """Novidade: 100 se produto novo, decai. Sem banco, assume novidade máxima."""
    # score_novidade é preenchido externamente se houver histórico.
    # Se não foi preenchido, assume novidade alta (bootstrap).
    if produto.score_novidade is not None:
        return produto.score_novidade
    return 80.0  # default: razoavelmente novo


def calcular_score(produto: Produto) -> float:
    """Calcula score 2.0 e salva no produto (in-place). Retorna o score."""
    s = (
        W_DESCONTO * _sub_desconto(produto)
        + W_AVALIACAO * _sub_avaliacao(produto)
        + W_SOCIAL * _sub_social(produto)
        + W_COMISSAO * _sub_comissao(produto)
        + W_NOVIDADE * _sub_novidade(produto)
    )

    if produto.historico_curto:
        s *= _PENALIDADE_HISTORICO_CURTO

    produto.score = round(s, 4)
    return produto.score
