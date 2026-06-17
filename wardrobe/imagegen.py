"""
Geração de imagem do look: dado os ids das peças, baixa as fotos e pede ao
Gemini (gemini-3.1-flash-image) uma foto editorial de uma modelo vestindo as
peças, aplicando a paleta da cliente. Reaproveita storage + style_profile.

Tratamento de 429:
- 429 transitório (estouro de RPM, ex.: cliques em sequência) -> retry com
  backoff exponencial + jitter; em geral resolve no 2º/3º try.
- 429 de cota dura (billing/plano/limite diário) -> sem retry (não adianta),
  mapeado direto para QuotaError para a camada de cima dar uma resposta gentil.
"""

import os

from google.genai import types
from google.genai.errors import APIError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from . import storage, style_profile
from .config import get_gemini_client

IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")


class ImageGenError(RuntimeError):
    """Falha ao gerar a imagem do look."""


class QuotaError(ImageGenError):
    """Cota/billing de geração de imagem indisponível na chave (429)."""


def _is_hard_quota(exc: BaseException) -> bool:
    """429 de cota dura (billing/plano/limite diário): retry não ajuda."""
    msg = str(exc).lower()
    code = getattr(exc, "code", None)
    is_429 = code == 429 or "429" in msg or "resource_exhausted" in msg
    if not is_429:
        return False
    return any(s in msg for s in ("billing", "plan", "per day", "daily", "free_tier"))


def _is_transient(exc: BaseException) -> bool:
    """429 transitório (RPM/burst de cliques) ou 5xx: vale retry com backoff."""
    code = getattr(exc, "code", None)
    if isinstance(exc, APIError) and isinstance(code, int) and code >= 500:
        return True
    msg = str(exc).lower()
    is_429 = code == 429 or "429" in msg or "resource_exhausted" in msg
    return is_429 and not _is_hard_quota(exc)


def _prompt(occasion, season) -> str:
    ctx = []
    if occasion:
        ctx.append(f"ocasião: {occasion.replace('_', ' ')}")
    if season:
        ctx.append(f"estação: {season}")
    ctx_s = "; ".join(ctx) or "uso geral do dia a dia"
    return (
        "Fotografia editorial de moda: uma modelo vestindo/usando as peças "
        "mostradas nas fotos de referência, combinadas como UM único look "
        f"coerente ({ctx_s}). Corpo inteiro, pose natural, fundo de estúdio "
        "clean e neutro, luz suave de lookbook. Mantenha fielmente as cores e o "
        "caimento das peças mostradas.\n" + style_profile.prompt_fragment()
    )


@retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.5, max=8),
    reraise=True,
)
def _call_gemini(parts: list):
    """Chamada à API com retry só nos 429 transitórios / 5xx."""
    client = get_gemini_client()
    return client.models.generate_content(
        model=IMAGE_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )


def generate_look_image(garment_ids: list[str], occasion=None, season=None) -> bytes:
    """Gera a imagem PNG do look. Lança QuotaError (429) ou ImageGenError."""
    parts: list = []
    for gid in garment_ids:
        img = storage.download_image(gid)
        if img:
            parts.append(types.Part.from_bytes(data=img, mime_type="image/jpeg"))
    if not parts:
        raise ImageGenError("nenhuma foto de peça disponível para o look")

    parts.append(_prompt(occasion, season))

    try:
        resp = _call_gemini(parts)
    except Exception as exc:  # noqa: BLE001 — classifica por mensagem/código
        msg = str(exc)
        if getattr(exc, "code", None) == 429 or "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            raise QuotaError(msg) from exc
        raise ImageGenError(msg) from exc

    for part in resp.candidates[0].content.parts:
        data = getattr(getattr(part, "inline_data", None), "data", None)
        if data:
            return data
    raise ImageGenError("o modelo não retornou imagem")
