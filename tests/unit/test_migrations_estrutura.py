"""Validação estrutural das migrations SEM precisar de um Postgres rodando.

Não substitui aplicar o SQL de verdade (isso acontece no `db migrate` contra o
banco real), mas pega de graça os erros mais comuns antes de subir a VM:
parênteses/aspas desbalanceados, FK para tabela inexistente, tabela duplicada,
e presença das tabelas/seed que o resto do sistema espera.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

# Tabelas que o resto do sistema (decisão, pipeline) assume existir.
TABELAS_ESPERADAS = {
    "platform", "niche", "category_source", "keyword", "product",
    "collection_run", "offer", "price_history", "whatsapp_group", "post", "config",
}

# Chaves de config que o motor de decisão vai ler.
CONFIG_ESPERADAS = {
    "dedup_threshold", "desconto_real_min", "top_por_disparo", "max_por_nicho",
    "real_discount_window_days", "min_amostras_hist", "repost_min_days",
    "repost_price_drop_pct",
}


def _sql_completo() -> str:
    arquivos = sorted(MIGRATIONS_DIR.glob("*.sql"))
    assert arquivos, "Nenhuma migration .sql encontrada"
    return "\n".join(a.read_text(encoding="utf-8") for a in arquivos)


def _sem_comentarios(sql: str) -> str:
    # Remove comentários de linha (-- ...) para a contagem de parênteses não
    # tropeçar em traços/parênteses dentro de comentários.
    linhas = [re.sub(r"--.*$", "", ln) for ln in sql.splitlines()]
    return "\n".join(linhas)


@pytest.fixture(scope="module")
def sql() -> str:
    return _sql_completo()


def test_parenteses_balanceados(sql):
    corpo = _sem_comentarios(sql)
    assert corpo.count("(") == corpo.count(")"), "Parênteses desbalanceados no SQL"


def test_aspas_simples_pares(sql):
    corpo = _sem_comentarios(sql)
    assert corpo.count("'") % 2 == 0, "Aspas simples desbalanceadas no SQL"


def test_todas_as_tabelas_presentes(sql):
    criadas = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", sql))
    faltando = TABELAS_ESPERADAS - criadas
    assert not faltando, f"Tabelas faltando: {faltando}"


def test_sem_tabela_duplicada(sql):
    criadas = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", sql)
    dup = {t for t in criadas if criadas.count(t) > 1}
    assert not dup, f"Tabelas declaradas mais de uma vez: {dup}"


def test_fks_apontam_para_tabelas_existentes(sql):
    criadas = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", sql))
    referenciadas = set(re.findall(r"REFERENCES (\w+)\s*\(", sql))
    orfas = referenciadas - criadas
    assert not orfas, f"FK referencia tabela inexistente: {orfas}"


def test_seed_de_config_presente(sql):
    semeadas = set(re.findall(r"\(\s*'([a-z_]+)',\s*[\d.]+", sql))
    faltando = CONFIG_ESPERADAS - semeadas
    assert not faltando, f"Config sem seed: {faltando}"


def test_plataformas_semeadas(sql):
    assert "'mercadolivre'" in sql and "'shopee'" in sql, "Plataformas não semeadas"
