#!/usr/bin/env python3
"""
Registra (ou remove) o webhook do bot no Telegram.

Uso:
    python scripts/set_webhook.py https://SEU-PROJETO.vercel.app/api/telegram
    python scripts/set_webhook.py --delete
    python scripts/set_webhook.py --info

Lê TELEGRAM_BOT_TOKEN e TELEGRAM_WEBHOOK_SECRET do ambiente (.env).
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
BASE = f"https://api.telegram.org/bot{TOKEN}"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    arg = sys.argv[1]

    if arg == "--info":
        print(httpx.get(f"{BASE}/getWebhookInfo").json())
    elif arg == "--delete":
        print(httpx.post(f"{BASE}/deleteWebhook").json())
    else:
        payload = {"url": arg, "allowed_updates": ["message", "callback_query"]}
        if SECRET:
            payload["secret_token"] = SECRET
        print(httpx.post(f"{BASE}/setWebhook", json=payload).json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
