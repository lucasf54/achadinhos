"""Repositório — grava Produto no banco (product + offer + price_history).

Princípio do schema: preço é separado da identidade.
- `product` = identidade estável (upsert por platform_id + source_id).
- `offer` = snapshot do preço naquela coleta (1 por produto por run).
- `price_history` = série temporal enxuta para calcular desconto real.

Todas as escritas recebem uma conexão psycopg aberta (injeção de dependência).
"""
from __future__ import annotations

import logging
from typing import Any

from luachadinhos.models.produto import Produto

logger = logging.getLogger(__name__)

_PLATFORM_IDS = {
    "mercadolivre": 1,
    "shopee": 2,
}


def _platform_id(plataforma: str) -> int:
    pid = _PLATFORM_IDS.get(plataforma)
    if pid is None:
        raise ValueError(f"Plataforma desconhecida: {plataforma}")
    return pid


def upsert_product(conn: Any, produto: Produto) -> int:
    """Insere ou atualiza a identidade do produto. Retorna product.id."""
    pid = _platform_id(produto.plataforma)
    row = conn.execute(
        """
        INSERT INTO product (platform_id, source_id, title, product_url, image_url, seller)
        VALUES (%(pid)s, %(sid)s, %(title)s, %(url)s, %(img)s, %(seller)s)
        ON CONFLICT (platform_id, source_id)
        DO UPDATE SET
            title        = EXCLUDED.title,
            product_url  = EXCLUDED.product_url,
            image_url    = EXCLUDED.image_url,
            seller       = EXCLUDED.seller,
            last_seen_at = now()
        RETURNING id
        """,
        {
            "pid": pid,
            "sid": produto.source_id,
            "title": produto.titulo[:120],
            "url": produto.url or None,
            "img": produto.imagem or None,
            "seller": produto.vendedor or None,
        },
    ).fetchone()
    return row[0]


def criar_run(conn: Any, slot: str, platform_id: int | None = None) -> int:
    """Cria um registro de collection_run. Retorna run.id."""
    row = conn.execute(
        """
        INSERT INTO collection_run (slot, platform_id)
        VALUES (%(slot)s, %(pid)s)
        RETURNING id
        """,
        {"slot": slot, "pid": platform_id},
    ).fetchone()
    return row[0]


def finalizar_run(
    conn: Any,
    run_id: int,
    n_collected: int,
    n_posted: int = 0,
    status: str = "ok",
) -> None:
    """Atualiza o run com as contagens finais."""
    conn.execute(
        """
        UPDATE collection_run
        SET finished_at = now(),
            n_collected = %(nc)s,
            n_posted    = %(np)s,
            status      = %(st)s
        WHERE id = %(rid)s
        """,
        {"rid": run_id, "nc": n_collected, "np": n_posted, "st": status},
    )


def inserir_offer(conn: Any, product_id: int, run_id: int, produto: Produto) -> int:
    """Insere snapshot de oferta. Retorna offer.id."""
    row = conn.execute(
        """
        INSERT INTO offer (
            product_id, run_id,
            price_current, price_original, price_installment,
            discount_pct, savings,
            rating, rating_count, sales,
            commission_pct, free_shipping,
            affiliate_link, is_official_link
        ) VALUES (
            %(prod_id)s, %(run_id)s,
            %(price)s, %(orig)s, %(inst)s,
            %(disc)s, %(sav)s,
            %(rat)s, %(rat_c)s, %(sales)s,
            %(comm)s, %(fship)s,
            %(alink)s, %(offic)s
        )
        ON CONFLICT (product_id, run_id) DO UPDATE SET
            price_current    = EXCLUDED.price_current,
            price_original   = EXCLUDED.price_original,
            discount_pct     = EXCLUDED.discount_pct,
            savings          = EXCLUDED.savings,
            affiliate_link   = EXCLUDED.affiliate_link,
            is_official_link = EXCLUDED.is_official_link
        RETURNING id
        """,
        {
            "prod_id": product_id,
            "run_id": run_id,
            "price": produto.preco_atual,
            "orig": produto.preco_original or None,
            "inst": produto.preco_parcelado or None,
            "disc": produto.desconto_pct,
            "sav": produto.economia,
            "rat": produto.avaliacao,
            "rat_c": produto.n_avaliacoes,
            "sales": produto.vendas,
            "comm": produto.comissao_pct,
            "fship": produto.frete_gratis,
            "alink": produto.link_afiliado or None,
            "offic": produto.link_oficial,
        },
    ).fetchone()
    return row[0]


def inserir_price_history(conn: Any, product_id: int, preco: float) -> None:
    """Insere um ponto na série temporal de preço."""
    conn.execute(
        "INSERT INTO price_history (product_id, price) VALUES (%s, %s)",
        (product_id, preco),
    )


def gravar_coleta(
    conn: Any,
    run_id: int,
    produtos: list[Produto],
) -> list[tuple[int, int]]:
    """Grava uma lista de produtos coletados (product + offer + price_history).

    Grava TODOS os produtos (o filtro vem depois), porque a série de preço
    precisa crescer mesmo para produtos que não serão postados neste disparo.

    Returns:
        Lista de (product_id, offer_id) para cada produto gravado.
    """
    resultado: list[tuple[int, int]] = []

    for p in produtos:
        try:
            product_id = upsert_product(conn, p)
            offer_id = inserir_offer(conn, product_id, run_id, p)
            inserir_price_history(conn, product_id, p.preco_atual)
            resultado.append((product_id, offer_id))
        except Exception:
            logger.error(
                "Erro ao gravar produto %s/%s",
                p.plataforma, p.source_id, exc_info=True,
            )
            continue

    logger.info("Gravados %d/%d produtos no banco", len(resultado), len(produtos))
    return resultado
