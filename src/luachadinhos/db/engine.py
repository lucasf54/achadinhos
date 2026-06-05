"""Conexão com o PostgreSQL e aplicação de migrations.

Mantém a dependência de psycopg isolada aqui. O resto do código pede uma
conexão via `conectar()` e não sabe detalhes do driver.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..config.settings import get_settings

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def conectar():
    """Abre uma conexão psycopg3 usando DATABASE_URL do .env.

    Import de psycopg é tardio (lazy) de propósito: assim o pacote importa e a
    CLI roda `--help` mesmo sem o driver instalado.
    """
    try:
        import psycopg
    except ImportError as e:  # pragma: no cover - mensagem de ajuda
        raise RuntimeError(
            "psycopg não instalado. Rode: pip install -r requirements.txt"
        ) from e

    settings = get_settings()
    return psycopg.connect(settings.database_url, autocommit=True)


def listar_migrations() -> list[Path]:
    """Retorna os .sql da pasta migrations em ordem (0001, 0002, ...)."""
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def aplicar_migrations() -> list[str]:
    """Aplica todas as migrations em ordem. Retorna os nomes aplicados.

    Cada arquivo é idempotente (IF NOT EXISTS / ON CONFLICT), então re-rodar
    é seguro. Numa Fase futura podemos adicionar uma tabela schema_migrations
    para pular as já aplicadas; por ora a idempotência basta.
    """
    aplicadas: list[str] = []
    with conectar() as conn:
        for arquivo in listar_migrations():
            sql = arquivo.read_text(encoding="utf-8")
            log.info("Aplicando migration %s", arquivo.name)
            conn.execute(sql)
            aplicadas.append(arquivo.name)
    return aplicadas
