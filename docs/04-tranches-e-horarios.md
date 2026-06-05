# Tranches, categorias e horários de publicação

Decisão de produto (junho/2026) sobre COMO dividir as ofertas nos disparos diários.

## Princípio: tranches, não fluxo contínuo

Não se posta o dia inteiro. São **3 disparos curados** ("tranches") em horários
de pico, cada um com um pacote de ofertas espaçadas dentro do bloco.

## Estratégia: HÍBRIDO (melhores + tema do horário)

Cada disparo de ~7-8 ofertas se divide em:
- **~5 vagas livres** = as melhores do momento por score (qualquer nicho) —
  garante que oferta excelente nunca fica de fora.
- **~2-3 vagas temáticas** = puxadas do "tema do horário" — dá personalidade.
- **Regra:** no máx 1 oferta por nicho no mesmo disparo (já existe: `max_por_nicho`).
- **Anti-repetição:** não repete o que já saiu no dia (banco controla).

## Volume

- **7-8 ofertas por disparo** → ~21-24/dia.
- Configurável via `top_por_disparo` (tabela `config` / .env). Começar aqui e ajustar.
- Dentro da tranche, ofertas saem **espaçadas** (~3-4 min, com jitter), não em rajada.

## Horários (otimizados p/ pico brasileiro)

| Slot | Horário | Estado de compra do público |
|---|---|---|
| `manha`  | **08:00** ☕ | em casa, café, organizando o dia → **necessidade/prático** |
| `almoco` | **13:00** 🍽️ | pausa do trabalho, scroll, agrado → **desejo/impulso** |
| `noite`  | **20:00** 🌙 | família junta, sem pressa → **decisão grande/ticket alto** |

> 20h rende mais que 19h no Brasil (picos: 12-13h e 20-21h). O HORÁRIO define o
> estado de compra; o DIA DA SEMANA ajusta a vibe por cima. Tudo configurável.

## Princípio central

> **Manhã = necessidade · Almoço = desejo impulsivo · Noite = decisão grande**
> Quanto mais caro/ponderado → mais à noite. Quanto mais impulso/barato → almoço.
> Quanto mais doméstico/rotina → manhã.

## Grade completa: horário × dia da semana

Os nichos abaixo são os do `decision/nichos.py`. A tranche temática puxa
preferencialmente destes; as vagas livres (maioria) trazem as melhores de qualquer nicho.

### Seg–Qui (rotina padrão)
- **08h ☕:** Casa & Decoração, Beleza, Pet, Saúde, Alimentos
- **13h 🍽️:** Celulares, Informática, Áudio, Games, Moda, Calçados
- **20h 🌙:** Eletrodomésticos, TV & Vídeo, Esporte, Bebê, Brinquedos, Ferramentas

### Sex–Sáb (lazer / sair / fim de semana)
- **08h ☕:** Beleza, Moda, Casa ("receber em casa")
- **13h 🍽️:** Moda, Calçados, Celulares, Áudio (gratificação reforçada)
- **20h 🌙:** Eletrodomésticos, Games, Esporte, TV, "achados da semana"

### Domingo (preparar a semana)
- **08h ☕:** Casa & Decoração, Alimentos (mercado), Pet, organização
- **13h 🍽️:** Celulares, Games, Moda casual
- **20h 🌙:** Bebê/Infantil, Casa, Alimentos, Saúde ("prep da semana", família junta)

> "Outros" e nichos não listados entram sempre como vaga livre.
> A variação por dia é refinamento — pode entrar numa 2ª fase (ver Status).

## Status de implementação (fases)

Sugestão de construir em camadas, da mais simples (já quase pronta) à mais rica:

**Fase 1 — base (quase pronta):**
- ✅ `max_por_nicho` (diversidade por disparo) — já existe no motor.
- ✅ Anti-repetição (não repete o que já saiu) — já existe (Bloco D/E).
- ✅ "Melhores por score" — já existe. → Lança como "só as melhores + diversidade".

**Fase 2 — tema por horário (a FAZER):**
- 🔨 Cota temática por slot: o `engine.decidir()` hoje faz "top-N diverso" sem viés
  de tema. Adicionar ~2-3 vagas que puxam do tema do slot. Trabalho do Bloco F.
- 🔧 Config sugerida: `tema_por_slot` (mapa slot→nichos), `vagas_tematicas` (qtd).

**Fase 3 — variação por dia da semana (refinamento):**
- 🔨 Trocar o mapa de tema conforme o dia (seg-qui / sex-sáb / domingo).
- 🔧 Estrutura sugerida: `tema_por_slot_e_dia` ou um dict aninhado {dia_tipo: {slot: nichos}}.
  Determinar dia_tipo a partir da data do disparo (data passada explícita, não Date.now
  no código de decisão puro).

> Recomendação: lançar Fase 1, validar no Telegram, depois Fase 2, depois Fase 3.
> Cada fase é incremental e não quebra a anterior.

## Resumo das decisões

| Item | Decisão |
|---|---|
| Estratégia | Híbrido (melhores + tema do horário + dia da semana) |
| Volume/disparo | 7-8 (~21-24/dia), configurável |
| Horários | 08h / 13h / 20h |
| Lógica de tema | manhã=necessidade · almoço=desejo · noite=decisão grande |
| Variação semanal | seg-qui rotina · sex-sáb lazer/moda · dom prep-da-semana |
| Diversidade | máx 1 por nicho/disparo |
| Espaçamento | ~3-4 min entre ofertas (anti-cansaço/anti-ban) |
