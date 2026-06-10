"""
Geração de imagem do look: dado os ids das peças, baixa as fotos e pede ao
Gemini (gemini-2.5-flash-image) uma foto editorial de uma modelo vestindo as
peças, aplicando a paleta da cliente. Reaproveita storage + style_profile.

Atenção: a geração de imagem exige cota/billing na chave do Gemini. Sem isso,
a API responde 429 RESOURCE_EXHAUSTED — mapeado para QuotaError para a camada de
cima dar uma resposta gentil.
"""

import os

from google.genai import types

from . import storage, style_profile
from .config import get_gemini_client

IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")


class ImageGenError(RuntimeError):
    """Falha ao gerar a imagem do look."""


class QuotaError(ImageGenError):
    """Cota/billing de geração de imagem indisponível na chave (429)."""


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

    client = get_gemini_client()
    try:
        resp = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=parts,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
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
