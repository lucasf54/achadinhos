# STATUS — onde paramos e o que vem agora

_Atualizado ao concluir o Bloco F (Fase 0 completa)._

## ✅ Concluído: Bloco A — Fundação (23 testes verdes)

| Passo | Entrega | Arquivos |
|---|---|---|
| 1 | Esqueleto do projeto | `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`, `src/luachadinhos/**/__init__.py`, `docker-compose.yml` |
| 2 | Migrations + banco | `migrations/0001_init.sql` (11 tabelas), `src/luachadinhos/db/engine.py`, `tests/unit/test_migrations_estrutura.py` |
| 3 | Modelo + firewall PT-BR | `models/produto.py`, `models/filtros.py`, `models/schema_ptbr.py`, `tests/unit/test_schema_ptbr.py` |
| 4 | Config central | `config/settings.py`, `config/runtime_config.py`, `tests/unit/test_config.py` |
| 5 | CLI raiz | `cli.py`, `__main__.py`, `tests/unit/test_cli.py` |

Verificar: `python -m pytest tests/unit -q` → 23 passed. `python -m luachadinhos --help` responde.

## ✅ VALIDAÇÃO: ML sem navegador CONFIRMADO (do IP BR)

Rodado `scripts/validar_ml_sem_navegador.py MLB1051` do PC do usuário (Brasil):
- HTTP **200**, 607 KB, **sem anti-bot/captcha**.
- Extraídos **44 produtos completos** (título + preço atual + preço original + ID)
  via `requests` puro, sem navegador. **A aposta central está provada.**
- Golden file salvo: `tests/fixtures/ml_ofertas_MLB1051.html` (pro parser testar offline).

**Estrutura real descoberta (arquitetura "polycard"):** cada card é uma lista de
componentes tipados:
- Título: `{"type":"title","id":"title","title":{"text":"..."}}`
- Preço atual: `{"type":"price","id":"price","price":{"value":1799,"currency":"BRL"}}`
- Preço riscado: `"previous_price":{"value":2855,...}`
- ID/permalink: `.../p/MLB47106610`

**2 armadilhas observadas (o parser de produção PRECISA tratar):**
1. **Janela fixa vaza para card vizinho** → parsear card-por-card delimitado, não por
   janela de N chars. Achar os limites de cada card no JSON.
2. **Preço de parcela confundido com preço à vista** (ex: "R$149,80 de R$2699") →
   distinguir `price.value` de `installments`/`price_total`. A lógica do legado
   (`ml_ofertas_categorias.py`) já faz isso — PORTAR, não reescrever.

## ✅ Concluído: Bloco B — Coletor ML SEM navegador (60 testes verdes)

| Passo | Entrega | Arquivos |
|---|---|---|
| 5 | Fetch /ofertas (requests, retry/backoff, anti-bot) | `collectors/ml/fetch.py`, `tests/unit/test_ml_fetch.py` |
| 6 | Parser hydration polycard → Produto (testado offline) | `collectors/ml/parser.py`, `tests/unit/test_ml_parser.py` |
| 7 | Desconto/economia + comissões (portado do legado) | `collectors/ml/desconto.py`, `tests/unit/test_ml_desconto.py` |
| 8 | Link de afiliado (createLink + fallback manual) | `collectors/ml/afiliado.py` |
| 9 | MLCollector integrado + CLI collect | `collectors/ml/collector.py`, `tests/unit/test_ml_collector.py` |

Verificar: `python -m pytest tests/unit -q` → 60 passed.
`python -m luachadinhos collect --fonte ml --dry-run` → 48 produtos de MLB1051.

**Estrutura do parser:** o JSON fica em `_n.ctx.r={...}` dentro de um `<script>`.
Caminho: `appProps.pageProps.data.items[*].card.components[]` — cada componente
tem type (title, price, reviews, shipping, seller, etc.) no formato "polycard".

## ✅ Concluído: Bloco C — Coletor Shopee (82 testes verdes)

| Passo | Entrega | Arquivos |
|---|---|---|
| 10a | API GraphQL com assinatura SHA256 | `collectors/shopee/api.py`, `tests/unit/test_shopee_api.py` |
| 10b | Parser nodes → Produto (PRICE_DIVISOR, normalização %) | `collectors/shopee/parser.py`, `tests/unit/test_shopee_parser.py` |
| 10c | ShopeeCollector integrado + CLI | `collectors/shopee/collector.py`, `tests/unit/test_shopee_collector.py` |

Verificar: `python -m pytest tests/unit -q` → 82 passed.
`python -m luachadinhos collect --fonte shopee --categorias "fone bluetooth"` (precisa SHOPEE_APP_ID/SECRET no .env).

**PRICE_DIVISOR:** default=1 (preço em reais). Se na prática vier em centavos,
ajustar para 100 ou 100000. Fixture de teste cobre divisor 100.

**[VALIDAR NA PRÁTICA]:** rodar com credenciais reais da Shopee e confirmar que
os preços saem corretos. Se necessário, ajustar PRICE_DIVISOR.

## ✅ Concluído: Bloco D — Camada de banco (111 testes verdes)

| Passo | Entrega | Arquivos |
|---|---|---|
| 11 | Repositório (upsert product, offer, price_history, collection_run) | `db/repository.py`, `tests/unit/test_repository.py` |
| 12 | Histórico (stats 30d, já_postado, registrar_post) | `db/historico.py`, `tests/unit/test_historico.py` |

Verificar: `python -m pytest tests/unit -q` → 111 passed.

**API do repositório:**
- `gravar_coleta(conn, run_id, produtos)` → grava TODOS (mesmo os que não serão postados)
  para a série de preço amadurecer.
- `stats_preco_30d(conn, pid)` → `Stats30d(media, minimo, n_amostras)` para desconto real.
- `stats_preco_30d_batch(conn, pids)` → versão batch (1 query).
- `ja_postado(conn, pid, gid)` → anti-repetição com regras de repost.
- `ja_postado_batch(conn, pids, gid)` → triagem rápida.
- `registrar_post(conn, pid, oid, gid, preco)` → marca como postado.

## ✅ Concluído: Bloco E — Motor de decisão (164 testes verdes)

| Passo | Entrega | Arquivos |
|---|---|---|
| 13 | Tokenizer + similaridade Jaccard | `decision/tokenizer.py`, `tests/unit/test_tokenizer.py` |
| 14 | Dedup cross-plataforma | `decision/dedup.py`, `tests/unit/test_dedup.py` |
| 15 | Anti-fake (desconto real) | `decision/anti_fake.py`, `tests/unit/test_anti_fake.py` |
| 16-17 | Score 2.0 (5 sub-scores ponderados) | `decision/score.py`, `tests/unit/test_score.py` |
| 18 | Nichos (classificação determinística) | `decision/nichos.py`, `tests/unit/test_nichos.py` |
| 19 | Engine decidir (pipeline completo) | `decision/engine.py`, `tests/unit/test_engine_decisao.py` |

Verificar: `python -m pytest tests/unit -q` → 164 passed.

**Pipeline:** dedup → nichos → desconto real → anti-fake → anti-repetição → score → top-N diverso.
Funciona com e sem banco (modo offline/bootstrap para dry-run).

## ✅ Concluído: Bloco F — Publicação (207 testes verdes)

| Passo | Entrega | Arquivos |
|---|---|---|
| 20 | Copy WA (hooks criativos + fechamentos) | `publishers/copy.py`, `tests/unit/test_copy_wa.py` |
| 21 | WhatsApp publisher + throttling anti-ban | `publishers/whatsapp.py`, `tests/unit/test_whatsapp_publisher.py` |
| 22 | Kill-switch (polling PARAR) + Notifier Telegram | `control/kill_switch.py`, `control/notifier.py`, `tests/unit/test_kill_switch.py`, `tests/unit/test_notifier.py` |
| 23 | Pipeline do slot (fim-a-fim) | `pipeline/slot.py`, `tests/unit/test_pipeline_slot.py` |
| 24 | CLI integrada (decide, run-slot) | `cli.py` atualizado |

Verificar: `python -m pytest tests/unit -q` → 207 passed.

**CLI completa:**
- `python -m luachadinhos collect --fonte ml --dry-run`
- `python -m luachadinhos decide --categorias MLB1051`
- `python -m luachadinhos run-slot --slot dev`

## ✅ FASE 0 COMPLETA — 24/24 passos implementados

Todos os 6 blocos (A–F) estão prontos com 207 testes verdes.

### Para colocar em produção na VM Oracle:

1. **Banco:** `python -m luachadinhos db migrate` (cria as 11 tabelas).
2. **Credenciais:** preencher `.env` (DATABASE_URL, MATT_WORD/TOOL, SHOPEE_APP_ID/SECRET,
   BOT_TOKEN, CHAT_ID, WHATSAPP_GROUP_IDS).
3. **WA Service:** subir `whatsapp-service/` (Node/Baileys) — POST /send, GET /health.
4. **Validar Shopee:** rodar `collect --fonte shopee` e checar PRICE_DIVISOR.
5. **Cron:** 3 disparos/dia → `python -m luachadinhos run-slot --slot {manha|almoco|noite}`.

### O que falta (fora da Fase 0):

- Micro-serviço WhatsApp Baileys (`whatsapp-service/`): scaffolding Node.
- Bot Telegram interativo (InlineKeyboard + callbacks).
- Coletor supermercado.
- Cron + docker-compose de produção.
- Calibração fina de pesos do score (após histórico 30d encher).

## Referência rápida do legado (pasta-mãe `../`)

- `ml_ofertas_categorias.py` — scraper ML atual (Playwright). A lógica de extração
  de campos, desconto, comissões e geração de link de afiliado vem daqui.
- `shopee_ofertas_categorias.py` — Shopee via API GraphQL (Bloco C).
- `bot_telegram.py` — dedup cross-plataforma, score, filtros (Bloco E).
- `ml_cookies.json` — cookies p/ gerar link oficial de afiliado do ML.

## Blocos seguintes (visão)

- **C** — Coletor Shopee (porta a API GraphQL; validar PRICE_DIVISOR).
- **D** — Camada de banco (repositório: grava product/offer/price_history; histórico 30d).
- **E** — Motor de decisão (dedup, anti-fake, anti-repetição, score 2.0, nichos).
- **F** — Publicação (WhatsApp service Node, throttling, kill-switch Telegram, cron).
