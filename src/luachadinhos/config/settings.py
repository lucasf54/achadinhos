"""Settings — configuração vinda do ambiente (.env).

Segredos, URLs e defaults de filtro. Carregado uma vez (cache) e lido por todo
o sistema. NÃO contém os thresholds editáveis em runtime (esses vêm da tabela
`config` via runtime_config.py); aqui ficam só os defaults de bootstrap.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Raiz do projeto (LU_ACHADINHOS_CLAUDE/)
ROOT = Path(__file__).resolve().parents[3]


def _carregar_env() -> None:
    load_dotenv(ROOT / ".env")


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key) or default)
    except (ValueError, TypeError):
        return default


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key) or default)
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True, slots=True)
class Settings:
    # ── Banco ────────────────────────────────────────────────────────────────
    database_url: str

    # ── Mercado Livre ────────────────────────────────────────────────────────
    matt_word: str
    matt_tool: str
    cookies_file: str

    # ── Shopee ───────────────────────────────────────────────────────────────
    shopee_app_id: str
    shopee_secret: str

    # ── Telegram ─────────────────────────────────────────────────────────────
    bot_token: str
    chat_id_autorizado: str

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    whatsapp_service_url: str
    whatsapp_group_ids: tuple[str, ...]

    # ── Telegram como canal de publicação ────────────────────────────────────
    telegram_channel_ids: tuple[str, ...]
    publish_via: str  # 'telegram' | 'whatsapp'

    # ── Mídia / operação ─────────────────────────────────────────────────────
    imagem_supermercado: str
    timezone: str

    # ── Defaults de filtro (bootstrap; runtime sobrepõe via tabela config) ──
    filtro_desconto_min: int
    filtro_avaliacao_min: float
    filtro_avaliacoes_min: int
    filtro_preco_max: int
    dedup_threshold: float
    top_por_disparo: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _carregar_env()
    grupos = os.getenv("WHATSAPP_GROUP_IDS", "")
    tg_channels = os.getenv("TELEGRAM_CHANNEL_IDS", "")
    return Settings(
        database_url=os.getenv("DATABASE_URL", "postgresql://lu:lu@localhost:5432/luachadinhos"),
        matt_word=os.getenv("MATT_WORD", ""),
        matt_tool=os.getenv("MATT_TOOL", ""),
        cookies_file=os.getenv("COOKIES_FILE", "secrets/ml_cookies.json"),
        shopee_app_id=os.getenv("SHOPEE_APP_ID", ""),
        shopee_secret=os.getenv("SHOPEE_SECRET", ""),
        bot_token=os.getenv("BOT_TOKEN", ""),
        chat_id_autorizado=os.getenv("CHAT_ID_AUTORIZADO", ""),
        whatsapp_service_url=os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:3000"),
        whatsapp_group_ids=tuple(g.strip() for g in grupos.split(",") if g.strip()),
        telegram_channel_ids=tuple(g.strip() for g in tg_channels.split(",") if g.strip()),
        publish_via=os.getenv("PUBLISH_VIA", "telegram"),
        imagem_supermercado=os.getenv("IMAGEM_SUPERMERCADO", ""),
        timezone=os.getenv("TZ", "America/Sao_Paulo"),
        filtro_desconto_min=_int("FILTRO_DESCONTO_MIN", 20),
        filtro_avaliacao_min=_float("FILTRO_AVALIACAO_MIN", 4.0),
        filtro_avaliacoes_min=_int("FILTRO_AVALIACOES_MIN", 100),
        filtro_preco_max=_int("FILTRO_PRECO_MAX", 0),
        dedup_threshold=_float("DEDUP_THRESHOLD", 0.55),
        top_por_disparo=_int("TOP_POR_DISPARO", 5),
    )
