"""CLI raiz do Lu Achadinhos 2.0.

Subcomandos (preenchidos ao longo dos blocos da Fase 0):
  db migrate            aplica as migrations no Postgres                 [pronto]
  db check              testa a conexão e lista as tabelas              [pronto]
  collect               coleta ofertas (ML/Shopee)                      [pronto]
  decide                roda o motor de decisão sobre coletados          [pronto]
  publish               publica no WhatsApp                              [pronto]
  run-slot              executa um disparo fim-a-fim                     [pronto]

Uso:
  python -m luachadinhos --help
  python -m luachadinhos db migrate
"""
from __future__ import annotations

import argparse
import logging
import sys

from . import __version__


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.DEBUG if verbose else logging.INFO,
    )


# ── db ───────────────────────────────────────────────────────────────────────
def _cmd_db(args) -> int:
    if args.acao == "migrate":
        from .db.engine import aplicar_migrations
        aplicadas = aplicar_migrations()
        print(f"✅ Migrations aplicadas: {', '.join(aplicadas) or '(nenhuma)'}")
        return 0
    if args.acao == "check":
        from .db.engine import conectar
        with conectar() as conn:
            rows = conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1"
            ).fetchall()
        print(f"✅ Conexão OK. {len(rows)} tabela(s): " +
              ", ".join(r[0] for r in rows))
        return 0
    return 1


# ── collect ──────────────────────────────────────────────────────────────────
def _cmd_collect(args) -> int:
    fonte = args.fonte
    categorias = args.categorias
    dry_run = args.dry_run

    if fonte in ("ml", "todas"):
        from .collectors.ml.collector import MLCollector
        if not categorias:
            categorias = ["MLB1051"]  # default: celulares
        collector = MLCollector()
        produtos = collector.coletar(categorias, dry_run=dry_run)
        print(f"\n{'[DRY-RUN] ' if dry_run else ''}Coletados: {len(produtos)} produtos ML")
        for i, p in enumerate(produtos[:5], 1):
            desc = f"{p.desconto_pct:.0f}% off" if p.desconto_pct else ""
            print(f"  {i}. [{desc}] {p.titulo[:60]}")
            print(f"     R${p.preco_original:.2f} → R${p.preco_atual:.2f} | {p.source_id}")
        if len(produtos) > 5:
            print(f"  ... e mais {len(produtos) - 5}")
        return 0

    if fonte in ("shopee", "todas"):
        from .collectors.shopee.collector import ShopeeCollector
        keywords = categorias if categorias else ["fone bluetooth"]
        collector = ShopeeCollector()
        produtos_shopee = collector.coletar(keywords)
        print(f"\nColetados: {len(produtos_shopee)} produtos Shopee")
        for i, p in enumerate(produtos_shopee[:5], 1):
            desc = f"{p.desconto_pct:.0f}% off" if p.desconto_pct else ""
            print(f"  {i}. [{desc}] {p.titulo[:60]}")
            print(f"     R${p.preco_original:.2f} → R${p.preco_atual:.2f} | {p.source_id}")
        if len(produtos_shopee) > 5:
            print(f"  ... e mais {len(produtos_shopee) - 5}")

    return 0


# ── decide ───────────────────────────────────────────────────────────────────
def _cmd_decide(args) -> int:
    """Coleta + decisão offline (dry-run, sem banco)."""
    from .collectors.ml.collector import MLCollector
    from .decision.engine import decidir
    from .publishers.copy import gerar_mensagens_batch

    categorias = args.categorias or ["MLB1051"]
    collector = MLCollector()
    produtos = collector.coletar(categorias, dry_run=True)
    print(f"Coletados: {len(produtos)} produtos")

    selecionados = decidir(produtos)
    gerar_mensagens_batch(selecionados)

    print(f"\nSelecionados: {len(selecionados)} produtos")
    for i, p in enumerate(selecionados, 1):
        print(f"\n  {i}. [{p.desconto_real or p.desconto_pct:.0f}% desc real] "
              f"{p.titulo[:55]}")
        print(f"     R${p.preco_original:.2f} → R${p.preco_atual:.2f} "
              f"| nicho={p.nicho} | score={p.score:.1f}")
        print(f"     {p.mensagem_wa[:100]}...")
    return 0


# ── run-slot ─────────────────────────────────────────────────────────────────
def _cmd_run_slot(args) -> int:
    """Executa um disparo.

    Por padrão roda em DRY-RUN (não grava no banco nem publica) — seguro p/ teste.
    Com --publicar, abre conexão com o banco, grava o histórico e publica de verdade
    (no canal definido por PUBLISH_VIA: telegram ou whatsapp).
    """
    from .pipeline.slot import executar_slot

    publicar = args.publicar
    conn = None
    try:
        if publicar:
            from .db.engine import conectar
            conn = conectar()

        selecionados = executar_slot(
            slot=args.slot,
            categorias_ml=args.categorias,
            conn=conn,
            dry_run=not publicar,
            no_publish=args.no_publish,
        )
    finally:
        if conn is not None:
            conn.close()

    tag = "" if publicar else "[DRY-RUN] "
    print(f"\n{tag}Slot '{args.slot}': {len(selecionados)} produtos selecionados")
    for i, p in enumerate(selecionados, 1):
        desc = p.desconto_real if p.desconto_real is not None else p.desconto_pct
        score = p.score if p.score is not None else 0.0
        print(f"  {i}. [{desc:.0f}%] {p.titulo[:55]} | {p.nicho} | score={score:.1f}")
    return 0


# ── stubs dos próximos blocos ────────────────────────────────────────────────
def _nao_implementado(nome: str):
    def _fn(args) -> int:
        print(f"⏳ '{nome}' ainda não implementado (chega num bloco futuro da Fase 0).")
        return 2
    return _fn


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="luachadinhos",
        description="Lu Achadinhos 2.0 — esteira de inteligência de ofertas (ML + Shopee → WhatsApp).",
    )
    p.add_argument("--version", action="version", version=f"luachadinhos {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="logs detalhados (DEBUG)")

    sub = p.add_subparsers(dest="comando", required=True, metavar="<comando>")

    # db
    p_db = sub.add_parser("db", help="operações de banco (migrate, check)")
    p_db.add_argument("acao", choices=["migrate", "check"], help="ação de banco")
    p_db.set_defaults(func=_cmd_db)

    # collect
    p_col = sub.add_parser("collect", help="coleta ofertas (ML/Shopee)")
    p_col.add_argument("--fonte", choices=["ml", "shopee", "todas"], default="todas")
    p_col.add_argument("--categorias", nargs="*", default=[])
    p_col.add_argument("--dry-run", action="store_true",
                       help="coleta sem gerar links de afiliado")
    p_col.set_defaults(func=_cmd_collect)

    # decide
    p_dec = sub.add_parser("decide", help="roda decisão offline (dry-run)")
    p_dec.add_argument("--categorias", nargs="*", default=["MLB1051"])
    p_dec.set_defaults(func=_cmd_decide)

    # publish
    p_pub = sub.add_parser("publish", help="publica no WhatsApp [requer WA service]")
    p_pub.add_argument("--teste", action="store_true",
                       help="envia apenas para o primeiro grupo")
    p_pub.set_defaults(func=_nao_implementado("publish"))

    # run-slot
    p_slot = sub.add_parser("run-slot", help="executa um disparo fim-a-fim")
    p_slot.add_argument("--slot", choices=["manha", "almoco", "noite", "dev"], default="dev")
    p_slot.add_argument("--publicar", action="store_true",
                        help="MODO REAL: grava no banco e publica (sem isto = dry-run seguro)")
    p_slot.add_argument("--no-publish", action="store_true",
                        help="coleta e decide e grava no banco, mas não publica")
    p_slot.add_argument("--categorias", nargs="*", default=None,
                        help="códigos ML específicos (sem isto = TODAS as categorias dos inputs/)")
    p_slot.set_defaults(func=_cmd_run_slot)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(getattr(args, "verbose", False))
    try:
        return args.func(args)
    except Exception as e:  # erro amigável; -v mostra o traceback
        if getattr(args, "verbose", False):
            raise
        print(f"❌ Erro: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
