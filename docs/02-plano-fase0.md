# Plano da Fase 0 — Lu Achadinhos 2.0

> Documento para leitura e aprovação. Consolidação de investigação, schema,
> arquitetura e lógica de decisão. Pontos incertos marcados **[VALIDAR NA PRÁTICA]**.

---

## 1. Resumo executivo

A Fase 0 transforma o pipeline atual (sem memória entre execuções) num sistema
com **memória de preço e de postagem**. Entrega:

1. **Banco PostgreSQL** com histórico de preço por produto + registro do que já foi postado.
2. **Coletor ML sem navegador** (requests no lugar de Playwright) — RAM de ~300-500 MB → ~30-50 MB.
3. **Motor de decisão** com desconto real, score 2.0, anti-repetição e nichos.
4. **Estrutura modular** testável, rodando em batch episódico (3 disparos/dia via cron), cabendo em 1 GB.

**Por que mata a repetição:** hoje o sistema é stateless. A Fase 0 adiciona:
- **Memória de postagem** (`post`): só repõe se passaram 30+ dias OU preço caiu 10%+.
- **Memória de preço** (`price_history`): desconto REAL (hoje vs média 30d) mata o desconto fake.
- **Novidade no score** + **diversidade por nicho** (máx 2/nicho/disparo): garante rotação.

---

## 2. Decisão: coletar ML SEM navegador ✅

Verificado por curl na investigação:

| Opção | Status | Veredito |
|---|---|---|
| API REST oficial (api.mercadolibre.com) | 403/401, exige OAuth + app aprovado (política abr/2025) | Descartada |
| **JSON embutido na /ofertas (requests)** | **HTTP 200 sem cookie**, traz todos os campos do scraper atual | **RECOMENDADA** — RAM 30-50 MB |
| Playwright (atual) | Funciona mas ~300-500 MB | Fallback só sob anti-bot |

**[VALIDAR NA PRÁTICA]:** (1) anti-bot/Cloudflare sob volume e da VM BR; (2) fragilidade
do parser de hydration; (3) renovação de cookies do `createLink`; (4) PRICE_DIVISOR Shopee.
Mitigações: golden file de teste, fallback Playwright, healthcheck de cookies, auto-detect.

Geração de link de afiliado (`createLink` via cookies) já usa requests — não muda.

---

## 3. Schema do banco (PostgreSQL)

Tabelas: `platform`, `niche`, `category_source`, `keyword`, `product`, `collection_run`,
`offer`, `price_history`, `whatsapp_group`, `post`, `config`. As 3 que atacam a dor:
**`price_history`** (desconto real), **`post`** (anti-repetição), **`config`** (thresholds editáveis).

> O SQL completo (CREATE TABLE de todas as tabelas + índices + seed da `config`) está
> em `migrations/0001_init.sql` quando implementarmos. Princípio central: **preço separado
> da identidade** — `product` é estável, preço vive em `offer`/`price_history`. É isso que
> viabiliza o desconto real. Dedup exato por `(platform_id, source_id)`; dedup por
> similaridade via `title_norm` + extensão `pg_trgm`.

Thresholds default (tabela `config`, editáveis sem deploy): desconto_real_min=15%,
min_savings=R$10, top_por_disparo=5, max_por_nicho=2, janela=30d, min_amostras=5,
repost_min_days=30, repost_price_drop=10%.

---

## 4. Estrutura de pastas

Raiz: `LU_ACHADINHOS_CLAUDE/`. Legado fica intocado na pasta-mãe como referência.

```text
LU_ACHADINHOS_CLAUDE/
├── README.md  pyproject.toml  requirements.txt  .env.example  .gitignore
├── docker-compose.yml  Makefile
├── docs/            # operação + adr/ (decisões: ml-sem-navegador, schema-ptbr, thresholds)
├── secrets/         # ml_cookies.json, shopee.key (gitignored)
├── data/            # runs/ e excel/ (efêmeros)
├── scripts/         # run_slot.sh (cron), healthcheck.sh, backup_db.sh
├── migrations/      # 0001_init.sql ...
├── inputs/          # .txt e .json legados (seed inicial)
├── whatsapp-service/# micro-serviço Node/Baileys (POST /send, /health)
├── tests/           # fixtures/ (golden html), unit/, integration/
└── src/luachadinhos/
    ├── cli.py                # collect|decide|publish|run-slot|db
    ├── config/  models/  db/
    ├── collectors/  # ml/ (fetch,parser,afiliado,desconto) shopee/ supermercado/
    ├── decision/    # tokenizer,similaridade,dedup,score,anti_fake,anti_repeticao,nichos
    ├── publishers/  # whatsapp.py, throttling.py, copy.py, excel.py
    ├── control/     # notifier.py, kill_switch.py
    └── pipeline/    # slot.py (executar_slot)
```

**Orçamento RAM:** postgres 256M + whatsapp 200M residentes (~456M em repouso 23h/dia);
app one-shot 384M só no slot → pico ~840M < 1 GB. O app não é daemon: acorda, roda, morre.

---

## 5. Lógica de decisão (fórmulas)

**Desconto real (anti-fake):**
```
ref           = 0.6*media30 + 0.4*min30
desconto_real = max(0, (ref - preco_hoje)/ref * 100)
→ descarta se desconto_real < 15% OU economia_real < R$10
```
Histórico curto (<5 amostras): fallback `min(desconto_card, 25)` + penaliza score em 0.90.
Bootstrap: funciona desde o dia 1, fica mais honesto conforme o histórico enche (~30 dias).

**Score 2.0** (sub-scores 0-100, ponderados):
```
0.30*desconto_real + 0.22*avaliacao + 0.20*social + 0.13*comissao + 0.15*novidade
(social = max(n_aval*7, vendas), equaliza ML↔Shopee; *0.90 se histórico curto)
```

**Anti-repetição:** repõe só se nunca postado, OU 30+ dias, OU preço caiu 10%+.

**Nichos:** cascata determinística (tokens do título → dicionário de nichos → fallback
por categoria → "Outros"). Sem ML/LLM em runtime.

**Seleção por disparo (N=5):** coleta tudo → dedup → **grava histórico de TODOS antes de
filtrar** (senão a curva 30d nunca amadurece) → desconto real + nicho → anti-fake →
anti-repetição → score → top-N com diversidade (máx 2/nicho) → marca postado → envia.

---

## 6. Checklist de implementação (24 passos, 6 blocos)

**A — Fundação:** (1) esqueleto+deps (2) migrations+Postgres docker (3) modelo interno+firewall PT-BR (4) config central.
**B — Coletor ML sem navegador:** (5) fetch /ofertas (6) parser hydration [crítico, golden file] (7) desconto+comissões (8) link afiliado (9) MLCollector integrado.
**C — Shopee:** (10) ShopeeCollector [validar PRICE_DIVISOR].
**D — Banco:** (11) engine+repositório (12) histórico (stats 30d, "já postado?").
**E — Decisão:** (13) tokenizer+similaridade (14) dedup cross (15) anti-fake (16) anti-repetição (17) score 2.0 (18) nichos (19) engine.decidir.
**F — Publicação:** (20) copy+Excel (21) WhatsApp service+publisher+throttling (22) kill-switch+notifier (23) pipeline do slot (24) cron+docker-compose.

Cada passo é testável isolado e construído sobre o anterior.

---

## 7. Fora da Fase 0 (depois)

Bot Telegram interativo de longa duração; coletor supermercado completo; grupos
temáticos por nicho; cota de comissão garantida; pipeline Playwright de produção;
calibração fina de pesos (após histórico encher); API REST oficial do ML; migração
de dados legados (começa com banco limpo).
