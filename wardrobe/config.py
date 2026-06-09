"""Carrega configuração de ambiente e instancia os clients (lazy + cacheado)."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Variável de ambiente obrigatória ausente."""


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(
            f"Variável de ambiente obrigatória ausente: {name}. "
            f"Copie .env.example para .env e preencha."
        )
    return value


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    supabase_url: str
    supabase_service_key: str
    supabase_bucket: str
    confidence_threshold: float
    # Telegram (usado só pelo bot serverless; opcional no fluxo batch)
    telegram_bot_token: str
    telegram_allowed_ids: frozenset[int]
    telegram_webhook_secret: str


def _parse_ids(raw: str) -> frozenset[int]:
    return frozenset(int(x) for x in raw.replace(";", ",").split(",") if x.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        gemini_api_key=_require("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        supabase_url=_require("SUPABASE_URL"),
        supabase_service_key=_require("SUPABASE_SERVICE_KEY"),
        supabase_bucket=os.getenv("SUPABASE_BUCKET", "wardrobe"),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.55")),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_allowed_ids=_parse_ids(os.getenv("TELEGRAM_ALLOWED_IDS", "")),
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
    )


@lru_cache(maxsize=1)
def get_gemini_client():
    from google import genai

    return genai.Client(api_key=get_settings().gemini_api_key)


@lru_cache(maxsize=1)
def get_supabase_client():
    from supabase import create_client

    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_key)
