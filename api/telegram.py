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
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(self.path)
        if parsed.path == "/api/look-image":
            self._look_image(parse_qs(parsed.query))
            return
        if parsed.path in ("/api/look", "/api/search", "/api/similar", "/api/capsule"):
            self._brain(parsed.path, parse_qs(parsed.query))
            return
        if parsed.path == "/api/process-queue":
            self._process_queue()
            return
        # healthcheck simples
        self._ok("guarda-roupa bot online")

    def _secret_ok(self) -> bool:
        secret = os.getenv("BRAIN_SECRET", "")
        if secret and self.headers.get("X-Brain-Secret", "") != secret:
            self.send_response(401)
            self.end_headers()
            return False
        return True

    def _json(self, status: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def _look_image(self, qs: dict) -> None:
        if not self._secret_ok():
            return
        ids = [x for x in (qs.get("ids", [""])[0] or "").split(",") if x]
        from wardrobe import imagegen

        try:
            png = imagegen.generate_look_image(
                ids, qs.get("occasion", [""])[0], qs.get("season", [""])[0]
            )
        except imagegen.QuotaError:
            self._json(503, {"error": "quota"})
            return
        except Exception:
            import logging

            logging.getLogger("api.telegram").exception("look-image falhou")
            self._json(502, {"error": "falha"})
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(png)

    def _process_queue(self) -> None:
        """Drena um lote da fila de ingestão (chamado pelo cron do Supabase)."""
        # Segredo dedicado ao trigger (cai no BRAIN_SECRET se QUEUE_SECRET não existir).
        want = os.getenv("QUEUE_SECRET") or os.getenv("BRAIN_SECRET", "")
        if want and self.headers.get("X-Queue-Secret", "") != want:
            self.send_response(401)
            self.end_headers()
            return
        from wardrobe import ingest_worker

        try:
            out = ingest_worker.process_pending()
        except Exception:
            import logging

            logging.getLogger("api.telegram").exception("process-queue falhou")
            self._json(500, {"error": "internal"})
            return
        self._json(200, out)

    def _brain(self, path: str, qs: dict) -> None:
        """Endpoints JSON do site (protegidos por segredo compartilhado)."""
        if not self._secret_ok():
            return

        from wardrobe import webapi

        try:
            k = max(1, min(20, int(qs.get("k", ["8"])[0])))
        except ValueError:
            k = 8

        try:
            if path == "/api/look":
                out = webapi.compose_look(
                    qs.get("occasion", [""])[0],
                    qs.get("season", [""])[0],
                    qs.get("temp", [""])[0],
                )
            elif path == "/api/similar":
                out = webapi.similar(qs.get("id", [""])[0], k)
            elif path == "/api/capsule":
                out = webapi.pack_capsule(
                    qs.get("days", [""])[0],
                    qs.get("occasion", [""])[0],
                    qs.get("night", [""])[0],
                    qs.get("season", [""])[0],
                )
            else:
                out = webapi.search((qs.get("q", [""])[0] or "").strip(), k)
        except Exception:
            import logging

            logging.getLogger("api.telegram").exception("brain falhou em %s", path)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"internal"}')
            return

        body = json.dumps(out, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

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
