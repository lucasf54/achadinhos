"""Pipeline do slot — executa um disparo fim-a-fim.

Orquestra: collect → gravar no banco → decidir → kill-switch → publish → registrar.

Modos:
- Completo (com banco + WA): produção na VM.
- Dry-run (sem banco, sem WA): local, mostra o que faria.
"""
from __future__ import annotations

import logging
from typing import Any

from luachadinhos.collectors.ml.collector import MLCollector
from luachadinhos.collectors.shopee.collector import ShopeeCollector
from luachadinhos.config.settings import get_settings
from luachadinhos.control.kill_switch import aguardar_confirmacao
from luachadinhos.control.notifier import TelegramNotifier
from luachadinhos.db.historico import ja_postado_batch, registrar_post
from luachadinhos.db.repository import criar_run, finalizar_run, gravar_coleta
from luachadinhos.decision.engine import decidir
from luachadinhos.models.filtros import Filtros
from luachadinhos.models.produto import Produto
from luachadinhos.publishers.copy import gerar_mensagens_batch
from luachadinhos.publishers.telegram import TelegramPublisher
from luachadinhos.publishers.whatsapp import WhatsAppPublisher

logger = logging.getLogger(__name__)


def _coletar_tudo(
    categorias_ml: list[str],
    keywords_shopee: list[str],
    filtros: Filtros,
    dry_run: bool,
) -> list[Produto]:
    """Coleta de todas as fontes."""
    todos: list[Produto] = []

    if categorias_ml:
        ml = MLCollector(filtros=filtros)
        todos.extend(ml.coletar(categorias_ml, dry_run=dry_run))

    if keywords_shopee:
        shopee = ShopeeCollector(filtros=filtros)
        todos.extend(shopee.coletar(keywords_shopee))

    return todos


def executar_slot(
    slot: str = "dev",
    categorias_ml: list[str] | None = None,
    keywords_shopee: list[str] | None = None,
    filtros: Filtros | None = None,
    conn: Any | None = None,
    dry_run: bool = False,
    no_publish: bool = False,
) -> list[Produto]:
    """Executa um disparo completo.

    Args:
        slot: identificador do disparo (manha, almoco, noite, dev).
        categorias_ml: códigos ML a coletar (default: MLB1051).
        keywords_shopee: keywords Shopee (default: vazio sem credenciais).
        filtros: parâmetros de filtragem/decisão.
        conn: conexão psycopg (None para dry-run).
        dry_run: se True, não grava no banco nem publica.
        no_publish: se True, não publica no WhatsApp (mas grava no banco).

    Returns:
        Lista de Produto selecionados para publicação.
    """
    settings = get_settings()
    if filtros is None:
        filtros = Filtros()
    if categorias_ml is None:
        categorias_ml = ["MLB1051"]
    if keywords_shopee is None:
        keywords_shopee = []

    logger.info("=== Disparo %s ===", slot)

    # ── 1. Coletar ──────────────────────────────────────────────────────────
    logger.info("Fase 1: Coleta")
    todos = _coletar_tudo(categorias_ml, keywords_shopee, filtros, dry_run)
    logger.info("Coletados: %d produtos", len(todos))

    if not todos:
        logger.warning("Nenhum produto coletado, abortando")
        return []

    # ── 2. Gravar TODOS no banco (série de preço) ──────────────────────────
    product_ids: dict[str, int] | None = None
    run_id: int | None = None

    if conn is not None and not dry_run:
        logger.info("Fase 2: Gravando no banco")
        run_id = criar_run(conn, slot)
        pares = gravar_coleta(conn, run_id, todos)
        # Mapa chave → product_id
        product_ids = {}
        for i, (pid, oid) in enumerate(pares):
            p = todos[i]
            product_ids[f"{p.plataforma}:{p.source_id}"] = pid

    # ── 3. Decidir ──────────────────────────────────────────────────────────
    logger.info("Fase 3: Decisão")

    # Anti-repetição: buscar postados recentes.
    # Depende só do banco — NÃO de ter canais configurados (publicar no chat
    # direto, com telegram_channel_ids vazio, também precisa não repetir).
    postados_ids: set[str] | None = None
    if conn is not None and product_ids:
        # Simplificação: checa contra o primeiro grupo
        first_group_id = 1  # ID do grupo no banco
        ids_banco = list(product_ids.values())
        bloqueados = ja_postado_batch(conn, ids_banco, first_group_id,
                                       repost_min_days=filtros.repost_min_days)
        # Converter de volta para chaves
        id_para_chave = {v: k for k, v in product_ids.items()}
        postados_ids = {id_para_chave[pid] for pid in bloqueados if pid in id_para_chave}

    selecionados = decidir(
        todos, filtros=filtros, conn=conn,
        product_ids=product_ids, postados_ids=postados_ids,
    )
    logger.info("Selecionados: %d produtos", len(selecionados))

    if not selecionados:
        logger.warning("Nenhum produto passou na decisão")
        if conn is not None and run_id is not None:
            finalizar_run(conn, run_id, n_collected=len(todos), status="ok")
        return []

    # ── 4. Gerar mensagens WA ───────────────────────────────────────────────
    logger.info("Fase 4: Gerando mensagens WA")
    gerar_mensagens_batch(selecionados)

    if dry_run or no_publish:
        logger.info("Modo %s — pulando publicação", "dry-run" if dry_run else "no-publish")
        if conn is not None and run_id is not None:
            finalizar_run(conn, run_id, n_collected=len(todos), status="ok")
        return selecionados

    # ── 5. Kill-switch ──────────────────────────────────────────────────────
    notifier = TelegramNotifier(settings.bot_token, settings.chat_id_autorizado)

    if notifier.configurado:
        logger.info("Fase 5: Kill-switch")
        notifier.avisar_inicio(slot, len(selecionados))
        prosseguir = aguardar_confirmacao(
            settings.bot_token, settings.chat_id_autorizado,
            espera_segundos=60,
        )
        if not prosseguir:
            logger.warning("Disparo cancelado pelo operador (kill-switch)")
            notifier.enviar(f"*Disparo {slot} CANCELADO* pelo operador.")
            if conn is not None and run_id is not None:
                finalizar_run(conn, run_id, n_collected=len(todos), status="cancelado")
            return []

    # ── 6. Publicar ──────────────────────────────────────────────────────────
    via = settings.publish_via
    logger.info("Fase 6: Publicação via %s", via)

    resultados: list[tuple[Produto, str, bool]] = []

    if via == "telegram":
        if not settings.bot_token:
            logger.error("BOT_TOKEN não configurado, abortando publicação")
            notifier.avisar_erro(slot, "BOT_TOKEN não configurado")
            if conn is not None and run_id is not None:
                finalizar_run(conn, run_id, n_collected=len(todos), status="failed")
            return selecionados

        tg = TelegramPublisher(bot_token=settings.bot_token)
        chat_ids = list(settings.telegram_channel_ids)
        if not chat_ids:
            # Fallback: publica no chat do operador
            chat_ids = [settings.chat_id_autorizado]
        resultados = tg.publicar(selecionados, chat_ids)

    else:  # whatsapp
        wa = WhatsAppPublisher(service_url=settings.whatsapp_service_url)
        if not wa.health_check():
            logger.error("WA service não disponível, abortando publicação")
            notifier.avisar_erro(slot, "WhatsApp service não disponível")
            if conn is not None and run_id is not None:
                finalizar_run(conn, run_id, n_collected=len(todos), status="failed")
            return selecionados
        group_ids = list(settings.whatsapp_group_ids)
        resultados = wa.publicar(selecionados, group_ids)

    n_enviados = sum(1 for _, _, ok in resultados if ok)

    # ── 7. Registrar posts no banco ─────────────────────────────────────────
    if conn is not None and product_ids:
        for produto, group_id_str, ok in resultados:
            if ok:
                chave = f"{produto.plataforma}:{produto.source_id}"
                pid = product_ids.get(chave)
                if pid:
                    registrar_post(
                        conn, product_id=pid, offer_id=None,
                        group_id=1,  # simplificação
                        preco=produto.preco_atual,
                        desconto=produto.desconto_real,
                        mensagem=produto.mensagem_wa,
                    )

    # ── 8. Finalizar ────────────────────────────────────────────────────────
    if conn is not None and run_id is not None:
        finalizar_run(conn, run_id, n_collected=len(todos),
                      n_posted=n_enviados, status="ok")

    if notifier.configurado:
        notifier.avisar_fim(slot, n_enviados, len(selecionados))

    logger.info("=== Disparo %s concluído: %d/%d enviados ===",
                slot, n_enviados, len(selecionados))
    return selecionados
