"""Publisher Telegram — envia ofertas via Bot API do Telegram.

Alternativa ao WhatsApp quando não há número sacrificável disponível.
Usa a Bot API REST diretamente (sem python-telegram-bot como dependência).

Publica em um ou mais chat_ids (grupos, canais ou chat direto).
Suporta envio de imagem + caption ou texto puro.
Throttling entre mensagens para não bater rate-limit do Telegram.
"""
from __future__ import annotations

import logging
import time

import requests

from luachadinhos.models.produto import Produto

logger = logging.getLogger(__name__)

_TG_SEND_MESSAGE = "https://api.telegram.org/bot{token}/sendMessage"
_TG_SEND_PHOTO = "https://api.telegram.org/bot{token}/sendPhoto"

# Delays entre mensagens (Telegram é mais tolerante que WA)
_DELAY_ENTRE_MSGS = 1.5  # segundos
_DELAY_ENTRE_CHATS = 3.0  # segundos


def _limpar_markdown(texto: str) -> str:
    """Remove formatação Markdown para fallback texto plano."""
    import re
    t = texto.replace("*", "").replace("~", "").replace("`", "")
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)  # [text](url) → text
    return t


class TelegramPublisher:
    """Envia ofertas como mensagens num canal/grupo/chat do Telegram."""

    def __init__(self, bot_token: str, timeout: int = 15):
        self.bot_token = bot_token
        self.timeout = timeout
        self._url_msg = _TG_SEND_MESSAGE.format(token=bot_token)
        self._url_photo = _TG_SEND_PHOTO.format(token=bot_token)

    def enviar_texto(self, chat_id: str, texto: str,
                     parse_mode: str = "Markdown") -> bool:
        """Envia mensagem de texto. Se Markdown falhar, retenta sem formatação."""
        try:
            r = requests.post(
                self._url_msg,
                json={
                    "chat_id": chat_id,
                    "text": texto,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=self.timeout,
            )
            data = r.json()
            if data.get("ok"):
                return True

            # Rate-limit: espera e retenta
            descr = data.get("description", "")
            if "Too Many Requests" in descr or r.status_code == 429:
                retry_after = data.get("parameters", {}).get("retry_after", 30)
                logger.warning("Rate-limit Telegram, aguardando %ds", retry_after)
                time.sleep(retry_after)
                return self.enviar_texto(chat_id, texto, parse_mode)

            # Markdown inválido: retenta sem parse_mode
            if "can't parse entities" in descr and parse_mode:
                logger.debug("Markdown falhou, reenviando sem formatação")
                return self.enviar_texto(chat_id, _limpar_markdown(texto),
                                         parse_mode="")

            logger.warning("Telegram sendMessage falhou: %s", descr)
            return False

        except Exception as exc:
            logger.error("Erro ao enviar Telegram: %s", exc)
            return False

    def enviar_com_imagem(self, chat_id: str, imagem_url: str,
                          caption: str) -> bool:
        """Envia foto com caption. Fallback para texto se falhar."""
        if not imagem_url:
            return self.enviar_texto(chat_id, caption)
        try:
            r = requests.post(
                self._url_photo,
                json={
                    "chat_id": chat_id,
                    "photo": imagem_url,
                    "caption": caption[:1024],  # limite do Telegram
                    "parse_mode": "Markdown",
                },
                timeout=self.timeout,
            )
            data = r.json()
            if data.get("ok"):
                return True

            descr = data.get("description", "")

            # Rate-limit
            if r.status_code == 429:
                retry_after = data.get("parameters", {}).get("retry_after", 30)
                logger.warning("Rate-limit Telegram (foto), aguardando %ds", retry_after)
                time.sleep(retry_after)
                return self.enviar_com_imagem(chat_id, imagem_url, caption)

            # Markdown inválido na caption: retenta sem parse_mode
            if "can't parse entities" in descr:
                logger.debug("Markdown na caption falhou, reenviando sem formatação")
                r2 = requests.post(
                    self._url_photo,
                    json={
                        "chat_id": chat_id,
                        "photo": imagem_url,
                        "caption": _limpar_markdown(caption)[:1024],
                    },
                    timeout=self.timeout,
                )
                if r2.json().get("ok"):
                    return True

            # Imagem pode falhar (URL expirado, etc) — fallback texto
            logger.debug("Foto falhou, enviando como texto: %s", descr)
            return self.enviar_texto(chat_id, caption)

        except Exception as exc:
            logger.error("Erro ao enviar foto Telegram: %s", exc)
            return self.enviar_texto(chat_id, caption)

    def publicar(
        self,
        produtos: list[Produto],
        chat_ids: list[str],
        com_imagem: bool = True,
    ) -> list[tuple[Produto, str, bool]]:
        """Publica produtos em todos os chats com throttling.

        Args:
            produtos: lista de Produto com mensagem_wa preenchida.
            chat_ids: IDs dos chats/canais/grupos destino.
            com_imagem: se True, tenta enviar com imagem do produto.

        Returns:
            Lista de (produto, chat_id, sucesso).
        """
        resultados: list[tuple[Produto, str, bool]] = []

        for ci, chat_id in enumerate(chat_ids):
            logger.info("Publicando em chat %s (%d/%d)...",
                        chat_id, ci + 1, len(chat_ids))

            for pi, produto in enumerate(produtos):
                msg = produto.mensagem_wa
                if not msg:
                    logger.warning("Produto sem mensagem: %s", produto.source_id)
                    resultados.append((produto, chat_id, False))
                    continue

                if com_imagem and produto.imagem:
                    ok = self.enviar_com_imagem(chat_id, produto.imagem, msg)
                else:
                    ok = self.enviar_texto(chat_id, msg)

                resultados.append((produto, chat_id, ok))

                if ok:
                    logger.info("[%d/%d] Enviado: %s",
                                pi + 1, len(produtos), produto.titulo[:50])
                else:
                    logger.error("[%d/%d] Falha: %s",
                                 pi + 1, len(produtos), produto.titulo[:50])

                if pi < len(produtos) - 1:
                    time.sleep(_DELAY_ENTRE_MSGS)

            if ci < len(chat_ids) - 1:
                time.sleep(_DELAY_ENTRE_CHATS)

        enviados = sum(1 for _, _, ok in resultados if ok)
        logger.info("Telegram: %d/%d mensagens enviadas em %d chat(s)",
                     enviados, len(resultados), len(chat_ids))
        return resultados
