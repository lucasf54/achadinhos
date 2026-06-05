"""Notificador Telegram — avisa o operador antes e depois dos disparos.

Envia mensagens simples via Bot API do Telegram. Não é interativo
(o bot interativo completo vem numa fase futura); por ora é unidirecional.
"""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    """Envia notificações ao operador via Telegram."""

    def __init__(self, bot_token: str, chat_id: str, timeout: int = 15):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self._url = _TG_API.format(token=bot_token)

    @property
    def configurado(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def enviar(self, texto: str, parse_mode: str = "Markdown") -> bool:
        """Envia mensagem de texto ao chat do operador."""
        if not self.configurado:
            logger.debug("Notifier não configurado, pulando mensagem")
            return False
        try:
            r = requests.post(
                self._url,
                json={
                    "chat_id": self.chat_id,
                    "text": texto,
                    "parse_mode": parse_mode,
                },
                timeout=self.timeout,
            )
            data = r.json()
            if not data.get("ok"):
                logger.warning("Telegram API erro: %s", data.get("description"))
                return False
            return True
        except Exception as exc:
            logger.error("Falha ao notificar Telegram: %s", exc)
            return False

    def avisar_inicio(self, slot: str, n_produtos: int) -> bool:
        return self.enviar(
            f"*Lu Achadinhos — Disparo {slot}*\n"
            f"{n_produtos} produtos selecionados.\n"
            f"Publicando em breve..."
        )

    def avisar_fim(self, slot: str, n_enviados: int, n_total: int) -> bool:
        return self.enviar(
            f"*Disparo {slot} concluído*\n"
            f"{n_enviados}/{n_total} mensagens enviadas."
        )

    def avisar_erro(self, slot: str, erro: str) -> bool:
        return self.enviar(f"*ERRO no disparo {slot}*\n`{erro[:500]}`")
