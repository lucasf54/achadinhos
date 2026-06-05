"""Engine de decisão — pipeline completo de seleção de ofertas.

Pipeline (do plano):
    coleta tudo → dedup → desconto real + nicho → anti-fake →
    anti-repetição → score → top-N com diversidade (máx 2/nicho)

Modos de operação:
- Com banco (conn != None): usa histórico real para desconto real e anti-repetição.
- Sem banco (conn == None): usa fallback (desconto do card, sem anti-repetição).
  Útil para dry-run e bootstrap.
"""
from __future__ import annotations

import logging
from typing import Any

from luachadinhos.db.historico import Stats30d, stats_preco_30d_batch
from luachadinhos.models.filtros import Filtros
from luachadinhos.models.produto import Produto

from .anti_fake import calcular_desconto_real, filtrar_anti_fake
from .dedup import dedup_similares
from .nichos import aplicar_nichos
from .score import calcular_score

logger = logging.getLogger(__name__)


def _aplicar_desconto_real_batch(
    produtos: list[Produto],
    product_ids: dict[str, int] | None,
    conn: Any | None,
    filtros: Filtros,
) -> None:
    """Calcula desconto real para todos os produtos."""
    if conn is None or product_ids is None:
        # Sem banco: fallback
        for p in produtos:
            calcular_desconto_real(p, stats=None, min_amostras=filtros.min_amostras_hist)
        return

    # Batch: busca stats de todos de uma vez
    ids = [pid for key, pid in product_ids.items() if pid]
    stats_map = stats_preco_30d_batch(conn, ids, janela_dias=filtros.janela_dias) if ids else {}

    for p in produtos:
        chave = f"{p.plataforma}:{p.source_id}"
        pid = product_ids.get(chave)
        stats = stats_map.get(pid) if pid else None
        calcular_desconto_real(p, stats=stats, min_amostras=filtros.min_amostras_hist)


def _selecionar_top_n_diverso(
    produtos: list[Produto],
    top_n: int,
    max_por_nicho: int,
) -> list[Produto]:
    """Seleciona top-N com diversidade por nicho.

    Ordena por score decrescente. Aceita até max_por_nicho do mesmo nicho.
    """
    ordenados = sorted(produtos, key=lambda p: p.score or 0, reverse=True)

    selecionados: list[Produto] = []
    contagem_nicho: dict[str, int] = {}

    for p in ordenados:
        nicho = p.nicho or "Outros"
        count = contagem_nicho.get(nicho, 0)
        if count >= max_por_nicho:
            continue
        selecionados.append(p)
        contagem_nicho[nicho] = count + 1
        if len(selecionados) >= top_n:
            break

    return selecionados


def decidir(
    produtos: list[Produto],
    filtros: Filtros | None = None,
    conn: Any | None = None,
    product_ids: dict[str, int] | None = None,
    postados_ids: set[str] | None = None,
) -> list[Produto]:
    """Pipeline completo de decisão.

    Args:
        produtos: lista de Produto coletados (todas as fontes).
        filtros: parâmetros de filtragem.
        conn: conexão psycopg (None para modo offline/dry-run).
        product_ids: mapa "plataforma:source_id" → product.id no banco.
        postados_ids: set de "plataforma:source_id" já postados recentemente.

    Returns:
        Lista final selecionada (top-N, diversa por nicho).
    """
    if filtros is None:
        filtros = Filtros()

    if not produtos:
        return []

    logger.info("Decisão: %d produtos de entrada", len(produtos))

    # 1. Dedup por similaridade de título
    candidatos = dedup_similares(produtos, threshold=filtros.dedup_threshold)

    # 2. Classificar nichos
    aplicar_nichos(candidatos)

    # 3. Desconto real (com ou sem banco)
    _aplicar_desconto_real_batch(candidatos, product_ids, conn, filtros)

    # 4. Anti-fake
    candidatos = filtrar_anti_fake(
        candidatos,
        desconto_real_min=filtros.desconto_real_min,
        min_savings_brl=filtros.min_savings_brl,
    )

    # 5. Anti-repetição (se temos info de postados)
    if postados_ids:
        antes = len(candidatos)
        candidatos = [
            p for p in candidatos
            if f"{p.plataforma}:{p.source_id}" not in postados_ids
        ]
        logger.info("Anti-repetição: %d → %d", antes, len(candidatos))

    # 6. Score 2.0
    for p in candidatos:
        calcular_score(p)

    # 7. Top-N com diversidade por nicho
    selecionados = _selecionar_top_n_diverso(
        candidatos,
        top_n=filtros.top_por_disparo,
        max_por_nicho=filtros.max_por_nicho,
    )

    logger.info(
        "Decisão final: %d selecionados de %d candidatos",
        len(selecionados), len(candidatos),
    )
    return selecionados
