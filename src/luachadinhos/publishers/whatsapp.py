"""Publisher WhatsApp — envia mensagens via micro-serviço Baileys.

O micro-serviço Node/Baileys roda em `whatsapp-service/` e expõe:
    POST /send  { groupId, message }  → { success: true }
    GET  /health                      → { status: "connected" }

Throttling humano anti-ban: delay aleatório entre mensagens.
"""
from __future__ import annotations

import logging
import random
import time

import requests

from luachadinhos.models.produto import Produto

logger = logging.getLogger(__name__)

# Delays anti-ban (em segundos)
_DELAY_MIN = 3.0
_DELAY_MAX = 8.0
_DELAY_ENTRE_GRUPOS = 10.0


class WhatsAppPublisher:
    """Envia mensagens para grupos de WhatsApp via micro-serviço Baileys."""

    def __init__(self, service_url: str = "http://localhost:3000", timeout: int = 15):
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout

    def health_check(self) -> bool:
        """Verifica se o serviço WA está conectado."""
        try:
            r = requests.get(f"{self.service_url}/health", timeout=self.timeout)
            data = r.json()
            ok = data.get("status") == "connected"
            if not ok:
                logger.warning("WA service não conectado: %s", data)
            return ok
        except Exception as exc:
            logger.error("WA service indisponível: %s", exc)
            return False

    def enviar_mensagem(self, group_id: str, mensagem: str) -> bool:
        """Envia uma mensagem para um grupo."""
        try:
            r = requests.post(
                f"{self.service_url}/send",
                json={"groupId": group_id, "message": mensagem},
                timeout=self.timeout,
            )
            data = r.json()
            if data.get("success"):
                return True
            logger.warning("WA send falhou: %s", data)
            return False
        except Exception as exc:
            logger.error("Erro ao enviar WA: %s", exc)
            return False

    def publicar(
        self,
        produtos: list[Produto],
        group_ids: list[str],
    ) -> list[tuple[Produto, str, bool]]:
        """Publica produtos em todos os grupos com throttling.

        Returns:
            Lista de (produto, group_id, sucesso).
        """
        resultados: list[tuple[Produto, str, bool]] = []

        for gi, group_id in enumerate(group_ids):
            logger.info("Publicando em grupo %s (%d/%d)...", group_id, gi + 1, len(group_ids))

            for pi, produto in enumerate(produtos):
                if not produto.mensagem_wa:
                    logger.warning("Produto sem mensagem WA: %s", produto.source_id)
                    resultados.append((produto, group_id, False))
                    continue

                ok = self.enviar_mensagem(group_id, produto.mensagem_wa)
                resultados.append((produto, group_id, ok))

                if ok:
                    logger.info(
                        "[%d/%d] Enviado: %s",
                        pi + 1, len(produtos), produto.titulo[:50],
                    )
                else:
                    logger.error(
                        "[%d/%d] Falha: %s",
                        pi + 1, len(produtos), produto.titulo[:50],
                    )

                # Throttling humano anti-ban
                if pi < len(produtos) - 1:
                    delay = random.uniform(_DELAY_MIN, _DELAY_MAX)
                    time.sleep(delay)

            # Delay entre grupos
            if gi < len(group_ids) - 1:
                time.sleep(_DELAY_ENTRE_GRUPOS)

        enviados = sum(1 for _, _, ok in resultados if ok)
        logger.info(
            "Publicação: %d/%d mensagens enviadas em %d grupo(s)",
            enviados, len(resultados), len(group_ids),
        )
        return resultados
