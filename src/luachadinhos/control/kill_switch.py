"""Kill-switch — permite cancelar um disparo antes de publicar.

Fluxo:
1. Notifica no Telegram: "Disparo X com N produtos. PARAR para cancelar."
2. Espera `espera_segundos` (default 60).
3. Checa se há resposta "PARAR" via Telegram getUpdates.
4. Se não houver → prossegue. Se houver → cancela.

Na fase atual (unidirecional), o kill-switch usa polling simples.
O bot interativo completo (com InlineKeyboard) vem numa fase futura.
"""
from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)

_TG_UPDATES = "https://api.telegram.org/bot{token}/getUpdates"


def verificar_parar(
    bot_token: str,
    chat_id: str,
    desde_update_id: int = 0,
    timeout: int = 10,
) -> tuple[bool, int]:
    """Checa se o operador mandou 'PARAR' no chat.

    Returns:
        (deve_parar, ultimo_update_id)
    """
    if not bot_token or not chat_id:
        return False, desde_update_id

    try:
        r = requests.get(
            _TG_UPDATES.format(token=bot_token),
            params={"offset": desde_update_id, "timeout": 0},
            timeout=timeout,
        )
        data = r.json()
        ultimo_id = desde_update_id

        for update in data.get("result", []):
            uid = update.get("update_id", 0)
            if uid >= ultimo_id:
                ultimo_id = uid + 1

            msg = update.get("message", {})
            if str(msg.get("chat", {}).get("id")) != str(chat_id):
                continue

            texto = (msg.get("text") or "").strip().upper()
            if texto == "PARAR":
                logger.warning("Kill-switch acionado pelo operador!")
                return True, ultimo_id

        return False, ultimo_id

    except Exception as exc:
        logger.error("Erro ao checar kill-switch: %s", exc)
        return False, desde_update_id


def aguardar_confirmacao(
    bot_token: str,
    chat_id: str,
    espera_segundos: int = 60,
    intervalo_poll: int = 5,
) -> bool:
    """Aguarda período e checa se operador mandou PARAR.

    Returns:
        True se deve prosseguir, False se cancelado.
    """
    if not bot_token or not chat_id:
        logger.info("Kill-switch não configurado, prosseguindo")
        return True

    logger.info("Aguardando %ds para kill-switch...", espera_segundos)
    update_id = 0

    # Limpa updates antigos
    _, update_id = verificar_parar(bot_token, chat_id, desde_update_id=0)

    inicio = time.time()
    while time.time() - inicio < espera_segundos:
        parar, update_id = verificar_parar(bot_token, chat_id, update_id)
        if parar:
            return False
        time.sleep(intervalo_poll)

    logger.info("Kill-switch: timeout sem PARAR, prosseguindo")
    return True
