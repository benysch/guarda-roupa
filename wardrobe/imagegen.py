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

import io
import logging
import os

from google.genai import types
from PIL import Image
from google.genai.errors import APIError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from . import storage, style_profile
from .config import get_gemini_client

logger = logging.getLogger(__name__)

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
        "Fotografia editorial de moda: uma modelo vestindo/usando TODAS as peças "
        "mostradas na imagem de referência (uma colagem com as peças do look), "
        f"combinadas como UM único look coerente ({ctx_s}). Corpo inteiro, pose "
        "natural, fundo de estúdio clean e neutro, luz suave de lookbook. Mantenha "
        "fielmente as cores e o caimento de cada peça mostrada.\n"
        + style_profile.prompt_fragment()
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


# Lado máximo da colagem de referência. O Gemini "tila" imagens em blocos de
# 768px (~258 tokens/tile); juntar TODAS as peças numa única imagem ≤768px deixa
# o request em ~1 tile (~258 tokens), em vez de N fotos grandes — o que estourava
# o limite de input tokens/minuto do free tier (orientação do suporte do Google).
REF_MAX_SIDE = 768


def _collage(images: list[bytes], max_side: int = REF_MAX_SIDE) -> bytes:
    """Monta UMA imagem (grade em fundo branco) com todas as peças do look."""
    pics = []
    for data in images:
        try:
            pics.append(Image.open(io.BytesIO(data)).convert("RGB"))
        except Exception:  # noqa: BLE001 — ignora foto ilegível
            continue
    if not pics:
        raise ImageGenError("nenhuma foto de peça disponível para o look")

    cols = 1 if len(pics) == 1 else 2
    rows = (len(pics) + cols - 1) // cols
    cell = max_side // cols
    canvas = Image.new("RGB", (cols * cell, rows * cell), "white")
    for i, pic in enumerate(pics):
        pic.thumbnail((cell, cell))
        x = (i % cols) * cell + (cell - pic.width) // 2
        y = (i // cols) * cell + (cell - pic.height) // 2
        canvas.paste(pic, (x, y))
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=85)
    return out.getvalue()


def generate_look_image(garment_ids: list[str], occasion=None, season=None) -> bytes:
    """Gera a imagem PNG do look. Lança QuotaError (429) ou ImageGenError."""
    raw = [img for gid in garment_ids if (img := storage.download_image(gid))]
    if not raw:
        raise ImageGenError("nenhuma foto de peça disponível para o look")

    # UMA colagem com todas as peças (input enxuto) + o prompt.
    parts: list = [
        types.Part.from_bytes(data=_collage(raw), mime_type="image/jpeg"),
        _prompt(occasion, season),
    ]

    try:
        resp = _call_gemini(parts)
    except Exception as exc:  # noqa: BLE001 — classifica por mensagem/código
        msg = str(exc)
        # diagnóstico: a mensagem bruta do Gemini distingue billing × modelo × limite
        logger.warning(
            "look-image falhou (modelo=%s, code=%s): %s",
            IMAGE_MODEL, getattr(exc, "code", None), msg[:400],
        )
        if getattr(exc, "code", None) == 429 or "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            raise QuotaError(msg) from exc
        raise ImageGenError(msg) from exc

    for part in resp.candidates[0].content.parts:
        data = getattr(getattr(part, "inline_data", None), "data", None)
        if data:
            return data
    raise ImageGenError("o modelo não retornou imagem")
