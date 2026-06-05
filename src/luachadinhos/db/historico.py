"""Consultas de histórico — stats 30d e anti-repetição.

Alimenta o motor de decisão com:
- Média/mínimo de preço dos últimos 30 dias (desconto real).
- Se o produto já foi postado recentemente (anti-repetição).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Stats30d:
    """Estatísticas de preço dos últimos N dias para um produto."""
    product_id: int
    media: float
    minimo: float
    n_amostras: int


def stats_preco_30d(
    conn: Any,
    product_id: int,
    janela_dias: int = 30,
) -> Stats30d | None:
    """Retorna média, mínimo e nº de amostras da série de preço.

    Returns:
        Stats30d ou None se não houver histórico.
    """
    row = conn.execute(
        """
        SELECT
            AVG(price)::NUMERIC(12,2)  AS media,
            MIN(price)::NUMERIC(12,2)  AS minimo,
            COUNT(*)                   AS n_amostras
        FROM price_history
        WHERE product_id = %(pid)s
          AND observed_at >= now() - make_interval(days := %(dias)s)
        """,
        {"pid": product_id, "dias": janela_dias},
    ).fetchone()

    if row is None or row[2] == 0:
        return None

    return Stats30d(
        product_id=product_id,
        media=float(row[0]),
        minimo=float(row[1]),
        n_amostras=int(row[2]),
    )


def stats_preco_30d_batch(
    conn: Any,
    product_ids: list[int],
    janela_dias: int = 30,
) -> dict[int, Stats30d]:
    """Versão batch de stats_preco_30d — 1 query para N produtos."""
    if not product_ids:
        return {}

    rows = conn.execute(
        """
        SELECT
            product_id,
            AVG(price)::NUMERIC(12,2)  AS media,
            MIN(price)::NUMERIC(12,2)  AS minimo,
            COUNT(*)                   AS n_amostras
        FROM price_history
        WHERE product_id = ANY(%(ids)s)
          AND observed_at >= now() - make_interval(days := %(dias)s)
        GROUP BY product_id
        """,
        {"ids": product_ids, "dias": janela_dias},
    ).fetchall()

    resultado: dict[int, Stats30d] = {}
    for row in rows:
        pid = int(row[0])
        resultado[pid] = Stats30d(
            product_id=pid,
            media=float(row[1]),
            minimo=float(row[2]),
            n_amostras=int(row[3]),
        )
    return resultado


def ja_postado(
    conn: Any,
    product_id: int,
    group_id: int,
    repost_min_days: int = 30,
    repost_price_drop_pct: float = 10.0,
    preco_atual: float | None = None,
) -> bool:
    """Verifica se o produto já foi postado recentemente neste grupo.

    Regras de anti-repetição:
    - Nunca postado → OK (False).
    - Postado há mais de repost_min_days → OK.
    - Preço caiu repost_price_drop_pct% desde o último post → OK.
    - Caso contrário → bloqueado (True).
    """
    row = conn.execute(
        """
        SELECT price_at_post, posted_at
        FROM post
        WHERE product_id = %(pid)s
          AND group_id   = %(gid)s
          AND status      = 'sent'
        ORDER BY posted_at DESC
        LIMIT 1
        """,
        {"pid": product_id, "gid": group_id},
    ).fetchone()

    if row is None:
        return False  # nunca postado

    preco_no_post = float(row[0])
    posted_at = row[1]

    # Checa se passaram dias suficientes
    dias_desde = conn.execute(
        "SELECT EXTRACT(DAY FROM now() - %s)::INT",
        (posted_at,),
    ).fetchone()[0]

    if dias_desde >= repost_min_days:
        return False  # tempo suficiente

    # Checa se preço caiu o suficiente
    if preco_atual is not None and preco_no_post > 0:
        queda_pct = (preco_no_post - preco_atual) / preco_no_post * 100
        if queda_pct >= repost_price_drop_pct:
            return False  # preço caiu bastante

    return True  # bloqueado


def ja_postado_batch(
    conn: Any,
    product_ids: list[int],
    group_id: int,
    repost_min_days: int = 30,
) -> set[int]:
    """Retorna set de product_ids que foram postados recentemente (bloqueados).

    Versão simplificada para triagem rápida (sem checar queda de preço).
    A checagem completa com preço é feita individualmente nos candidatos.
    """
    if not product_ids:
        return set()

    rows = conn.execute(
        """
        SELECT DISTINCT product_id
        FROM post
        WHERE product_id = ANY(%(ids)s)
          AND group_id   = %(gid)s
          AND status      = 'sent'
          AND posted_at  >= now() - make_interval(days := %(dias)s)
        """,
        {"ids": product_ids, "gid": group_id, "dias": repost_min_days},
    ).fetchall()

    return {int(r[0]) for r in rows}


def registrar_post(
    conn: Any,
    product_id: int,
    offer_id: int | None,
    group_id: int,
    preco: float,
    desconto: float | None = None,
    mensagem: str = "",
    status: str = "sent",
) -> int:
    """Registra que um produto foi postado num grupo. Retorna post.id."""
    row = conn.execute(
        """
        INSERT INTO post (product_id, offer_id, group_id,
                          price_at_post, discount_at_post, message_sent, status)
        VALUES (%(pid)s, %(oid)s, %(gid)s, %(price)s, %(disc)s, %(msg)s, %(st)s)
        RETURNING id
        """,
        {
            "pid": product_id,
            "oid": offer_id,
            "gid": group_id,
            "price": preco,
            "disc": desconto,
            "msg": mensagem[:2000] if mensagem else None,
            "st": status,
        },
    ).fetchone()
    return row[0]
