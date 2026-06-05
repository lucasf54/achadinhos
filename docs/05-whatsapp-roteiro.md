# Roteiro do WhatsApp (não-oficial, via Baileys)

> Status: planejado, NÃO implementado. O sistema publica no Telegram hoje.
> O WhatsApp entra quando o usuário tiver o chip dedicado.
> Troca de canal: variável `PUBLISH_VIA` (telegram | whatsapp) no .env.

## O que o usuário precisa providenciar (físico)

1. **Chip de celular dedicado/sacrificável** (pré-pago barato) — NUNCA o número
   pessoal. Se a Meta banir (risco real), troca o chip sem perder nada.
2. **Ativar o WhatsApp** nesse número num celular (receber o SMS de registro).
3. **"Esquentar" o número** por alguns dias antes de automatizar: usar normal
   (conversar, entrar em grupos). Número novo + automação em massa = ban rápido.

## O que falta construir (código)

4. **Serviço Node/Baileys** na VM (`whatsapp-service/`): micro-serviço que mantém
   a sessão do WhatsApp e expõe `POST /send` e `/health`. O esqueleto do publisher
   Python já existe (`publishers/whatsapp.py`), falta o serviço Node que ele chama.
5. **Login via QR Code**: o serviço mostra um QR no log; o usuário abre o WhatsApp
   do chip → Aparelhos conectados → Conectar aparelho → lê o QR. A VM fica "logada"
   como um aparelho (igual web.whatsapp.com), e mantém a sessão sozinha.
6. **Throttling anti-ban**: postar espaçado (jitter humano, ~minutos entre msgs),
   limite diário, horários humanos. O `publishers/throttling.py` cobre parte disso.
7. **Teste num grupo do próprio usuário** antes dos grupos reais.

## Configuração quando for ativar

- `.env`: `PUBLISH_VIA=whatsapp`, `WHATSAPP_SERVICE_URL=http://localhost:3000`,
  `WHATSAPP_GROUP_IDS=<ids dos grupos>`.
- O `whatsapp_group` no banco precisa dos grupos reais (hoje só tem o id=1 placeholder).

## O que NÃO é preciso

- ❌ Cadastro na Meta / WhatsApp Business API (esse seria o caminho oficial, pago
  e burocrático). Aqui é automação não-oficial: grátis, mas com risco de ban.
- ❌ Pagar nada. ❌ Verificação de empresa.

## Riscos (ser honesto com o usuário)

- **Ban do número**: real. Mitigar com chip dedicado + esquentar + throttle.
- **Postar em grupos** é o que mais "queima" o número.
- **Manutenção**: sessão pode cair (religar QR); o chip precisa de internet de
  vez em quando pra não derrubar a sessão.
- **Não-oficial**: a Meta pode mudar e quebrar; é caminho "gambiarra" que funciona.

## Vantagem da arquitetura atual

O publisher é trocável (PUBLISH_VIA). Telegram já valida todo o pipeline sem risco.
Quando o WhatsApp entrar, é só plugar — coleta/decisão/anti-fake/score não mudam.
