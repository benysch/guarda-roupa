"""
Webhook do Telegram — função Python serverless da Vercel.

Mantida fina de propósito: valida o segredo, lê o update e delega toda a lógica
para wardrobe.telegram_bot.handle_update. Processa inline (Fluid Compute +
maxDuration no vercel.json); o Telegram aguarda o 200 sem reenviar.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# garante que o pacote `wardrobe` (na raiz do repo) seja importável na Vercel
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wardrobe.config import get_settings  # noqa: E402
from wardrobe.telegram_bot import handle_update  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _ok(self, body: str = "ok") -> None:
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self) -> None:
        # healthcheck simples
        self._ok("guarda-roupa bot online")

    def do_POST(self) -> None:
        settings = get_settings()

        # verificação do segredo do webhook (defesa contra chamadas forjadas)
        secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if settings.telegram_webhook_secret and secret != settings.telegram_webhook_secret:
            self.send_response(401)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            update = json.loads(raw)
            handle_update(update)
        except Exception:  # sempre 200 para o Telegram não ficar reenviando
            import logging

            logging.getLogger("api.telegram").exception("falha no webhook")

        self._ok()
