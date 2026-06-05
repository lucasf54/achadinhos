-- ════════════════════════════════════════════════════════════════════════════
--  Lu Achadinhos 2.0 — Migration 0001 (schema inicial)
--
--  Roda uma vez num banco limpo. Idempotente: usa IF NOT EXISTS onde possível.
--  Princípio central: PREÇO É SEPARADO DA IDENTIDADE.
--    - `product`        = identidade estável (nunca muda) — SEM preço.
--    - `offer`          = snapshot por coleta (preço naquele momento).
--    - `price_history`  = série temporal enxuta p/ calcular desconto REAL.
--  As 3 tabelas que atacam a dor de "produto repetido":
--    price_history (desconto real) · post (anti-repetição) · config (thresholds).
-- ════════════════════════════════════════════════════════════════════════════

-- ── Extensões ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- similaridade de título (dedup)

-- ── 1) PLATAFORMA ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS platform (
    id            SMALLINT PRIMARY KEY,
    code          TEXT NOT NULL UNIQUE,              -- 'mercadolivre' | 'shopee'
    label         TEXT NOT NULL,
    price_divisor NUMERIC(12,4) NOT NULL DEFAULT 1,  -- Shopee: ajustar empiricamente
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);
INSERT INTO platform (id, code, label, price_divisor) VALUES
    (1, 'mercadolivre', 'Mercado Livre', 1),
    (2, 'shopee',       'Shopee',        1)
ON CONFLICT (id) DO NOTHING;

-- ── 2) NICHO (categoria de negócio, editável) ────────────────────────────────
CREATE TABLE IF NOT EXISTS niche (
    id         SERIAL PRIMARY KEY,
    slug       TEXT NOT NULL UNIQUE,
    label      TEXT NOT NULL,
    emoji      TEXT,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── 3) MAPA NICHO -> SELETOR POR PLATAFORMA (substitui os .txt) ──────────────
CREATE TABLE IF NOT EXISTS category_source (
    id             SERIAL PRIMARY KEY,
    niche_id       INT NOT NULL REFERENCES niche(id) ON DELETE CASCADE,
    platform_id    SMALLINT NOT NULL REFERENCES platform(id),
    selector_type  TEXT NOT NULL CHECK (selector_type IN ('category_code','search_keyword')),
    selector_value TEXT NOT NULL,                    -- 'MLB1051' ou 'celular'
    default_commission_pct NUMERIC(5,2),
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (platform_id, selector_value)
);
CREATE INDEX IF NOT EXISTS idx_catsource_niche ON category_source(niche_id);

-- ── 4) KEYWORD (sinônimos / stopwords / comissões / supermercado / blocklist) ─
CREATE TABLE IF NOT EXISTS keyword (
    id          SERIAL PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN
                  ('synonym_group','stopword','commission','supermarket','blocklist')),
    term        TEXT NOT NULL,
    group_label TEXT,                                -- synonym_group: 'fritadeira'
    value_num   NUMERIC(8,3),                        -- commission: 9.5
    payload     JSONB,                               -- supermarket: {obrigatorias,marcas,unidade}
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (kind, term)
);
CREATE INDEX IF NOT EXISTS idx_keyword_kind  ON keyword(kind) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_keyword_group ON keyword(group_label) WHERE kind = 'synonym_group';

-- ── 5) PRODUTO (identidade estável; SEM preço) ───────────────────────────────
CREATE TABLE IF NOT EXISTS product (
    id            BIGSERIAL PRIMARY KEY,
    platform_id   SMALLINT NOT NULL REFERENCES platform(id),
    source_id     TEXT NOT NULL,                     -- 'MLB123...' | 'itemId_shopId'
    niche_id      INT REFERENCES niche(id),
    title         TEXT NOT NULL,
    title_norm    TEXT,                              -- tokenizado/sem stopwords (cache dedup)
    product_url   TEXT,
    image_url     TEXT,
    seller        TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (platform_id, source_id)
);
CREATE INDEX IF NOT EXISTS idx_product_niche      ON product(niche_id);
CREATE INDEX IF NOT EXISTS idx_product_title_trgm ON product USING gin (title_norm gin_trgm_ops);

-- ── 6) RUN DE COLETA (manhã/almoço/noite) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS collection_run (
    id          BIGSERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    slot        TEXT NOT NULL CHECK (slot IN ('manha','almoco','noite','dev')),
    run_date    DATE NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo')::date,
    platform_id SMALLINT REFERENCES platform(id),    -- NULL = run combinada
    n_collected INT DEFAULT 0,
    n_posted    INT DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running','ok','partial','failed','cancelado')),
    notes       TEXT,
    UNIQUE (run_date, slot, platform_id)
);
CREATE INDEX IF NOT EXISTS idx_run_date ON collection_run(run_date DESC, slot);

-- ── 7) OFERTA (snapshot por produto por run; coração do histórico) ───────────
CREATE TABLE IF NOT EXISTS offer (
    id                BIGSERIAL PRIMARY KEY,
    product_id        BIGINT NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    run_id            BIGINT NOT NULL REFERENCES collection_run(id) ON DELETE CASCADE,
    collected_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    price_current     NUMERIC(12,2) NOT NULL,         -- "Preço à Vista/PIX"
    price_original    NUMERIC(12,2),                  -- riscado (do card)
    price_installment NUMERIC(12,2),
    discount_pct      NUMERIC(5,2) DEFAULT 0,         -- desconto do card (propaganda)
    savings           NUMERIC(12,2) DEFAULT 0,
    rating            NUMERIC(3,2),
    rating_count      INT,                            -- ML
    sales             INT,                            -- Shopee
    commission_pct    NUMERIC(5,2),
    free_shipping     BOOLEAN,
    affiliate_link    TEXT,
    is_official_link  BOOLEAN DEFAULT FALSE,          -- meli.la/matt_gen ok?
    wa_message        TEXT,
    score             NUMERIC(7,4),
    is_real_discount  BOOLEAN,                        -- preenchido na inserção (vs média 30d)
    avg_price_30d     NUMERIC(12,2),
    UNIQUE (product_id, run_id)
);
CREATE INDEX IF NOT EXISTS idx_offer_product_time ON offer(product_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_offer_run          ON offer(run_id);
CREATE INDEX IF NOT EXISTS idx_offer_score        ON offer(score DESC);
CREATE INDEX IF NOT EXISTS idx_offer_real_disc    ON offer(product_id) WHERE is_real_discount;

-- ── 8) HISTÓRICO DE PREÇO (série temporal enxuta -> média 30d) ───────────────
CREATE TABLE IF NOT EXISTS price_history (
    id          BIGSERIAL PRIMARY KEY,
    product_id  BIGINT NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    price       NUMERIC(12,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pricehist_product_time ON price_history(product_id, observed_at DESC);

-- ── 9) GRUPOS DE WHATSAPP ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS whatsapp_group (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    wa_group_id TEXT UNIQUE,
    niche_id    INT REFERENCES niche(id),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

-- ── 10) POST (memória do que foi postado -> anti-repetição) ──────────────────
CREATE TABLE IF NOT EXISTS post (
    id               BIGSERIAL PRIMARY KEY,
    product_id       BIGINT NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    offer_id         BIGINT REFERENCES offer(id),
    group_id         INT NOT NULL REFERENCES whatsapp_group(id),
    posted_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    price_at_post    NUMERIC(12,2) NOT NULL,          -- regra "caiu mais"
    discount_at_post NUMERIC(5,2),
    message_sent     TEXT,
    status           TEXT NOT NULL DEFAULT 'sent'
                       CHECK (status IN ('sent','failed','skipped'))
);
CREATE INDEX IF NOT EXISTS idx_post_product_time ON post(product_id, posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_post_group_time   ON post(group_id, posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_post_dedupe       ON post(product_id, group_id, posted_at DESC)
                                                  WHERE status = 'sent';

-- ── 11) CONFIG (thresholds / pesos editáveis sem deploy) ─────────────────────
CREATE TABLE IF NOT EXISTS config (
    key         TEXT PRIMARY KEY,
    value       NUMERIC NOT NULL,
    description TEXT
);
INSERT INTO config (key, value, description) VALUES
    ('dedup_threshold',           0.55, 'Jaccard p/ considerar produtos iguais'),
    ('send_similarity',           0.35, 'Similaridade máx entre itens enviados no mesmo disparo'),
    ('same_group_bonus',          0.50, 'Bônus de similaridade p/ mesmo grupo de sinônimos'),
    ('min_savings_brl',          10.00, 'Economia mínima eliminatória (R$)'),
    ('discount_cap_pct',         60.00, 'Teto de desconto no score'),
    ('desconto_real_min',        15.00, 'Corte anti-fake (% desconto real)'),
    ('top_por_disparo',           5,    'Máx ofertas enviadas por disparo'),
    ('max_por_nicho',             2,    'Diversidade: máx do mesmo nicho por disparo'),
    ('real_discount_window_days', 30,   'Janela da média p/ desconto real'),
    ('min_amostras_hist',         5,    'Nº mín de amostras p/ desconto real confiável'),
    ('repost_min_days',           30,   'Dias mínimos p/ repostar o mesmo produto'),
    ('repost_price_drop_pct',     10,   'Queda de preço (%) que libera repost antes do prazo'),
    ('purge_history_days',        40,   'Histórico de preço mais antigo que isto é purgado')
ON CONFLICT (key) DO NOTHING;
