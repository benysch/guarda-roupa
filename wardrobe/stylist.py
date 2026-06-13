"""
IA estilista MULTIMODAL: monta UM look escolhendo entre peças reais e explica o
porquê, aplicando o perfil de coloração da cliente (style_profile). Além dos
atributos em texto, manda as FOTOS reais ao Gemini — assim ele julga a cor e a
textura de verdade (crucial para coloração pessoal), não só a cor-família grossa.

Híbrido: o motor de regras (looks.py) fornece os candidatos válidos; aqui o
Gemini exerce o "bom gosto". Fica preso ao conjunto fornecido (referencia por
id), então não inventa roupa. Para segurar custo/latência, manda no máximo
MAX_IMAGES fotos (as mais relevantes da ocasião, baixadas em paralelo).
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from . import storage, style_profile
from .config import get_gemini_client, get_settings

logger = logging.getLogger(__name__)

# Teto de fotos enviadas por look (bound de custo/latência). looks.candidates já
# prioriza as peças da ocasião, então o corte pega as mais relevantes.
MAX_IMAGES = 12


class StyledLook(BaseModel):
    """Look escolhido pelo estilista, referenciando peças pelo id."""

    garment_ids: list[str] = Field(
        description="IDs das peças que compõem o look, SOMENTE da lista fornecida."
    )
    rationale: str = Field(
        description="Justificativa curta (1-2 frases, pt-BR) do look e das cores escolhidas."
    )


class StylistError(RuntimeError):
    """Falha definitiva do estilista (após retries)."""


def _facets(g: dict) -> str:
    bits = [
        g.get("subcategory") or g.get("category"),
        g.get("primary_color"),
        g.get("material"),
        g.get("pattern"),
        g.get("formality"),
        g.get("brand"),
    ]
    return ", ".join(str(b) for b in bits if b)


_TEMP_GUIDANCE = {
    "frio": "Está FRIO (abaixo de ~15°C): priorize AGASALHO (inclua um casaco/jaqueta "
    "se houver) e tecidos quentes (lã, tricô, couro); evite peças muito leves.",
    "ameno": "Temperatura AMENA (~15–24°C): camadas leves; casaco fino é opcional.",
    "quente": "Está QUENTE (acima de ~24°C): NÃO use casaco nem agasalho; prefira tecidos "
    "leves e frescos (linho, algodão, viscose) e peças arejadas.",
}


def _instructions(occasion, season, temperature=None) -> str:
    ctx = []
    if occasion:
        ctx.append(f"ocasião: {occasion.replace('_', ' ')}")
    if season:
        ctx.append(f"estação: {season}")
    ctx_s = "; ".join(ctx) or "uso geral do dia a dia"
    temp_line = _TEMP_GUIDANCE.get(temperature or "", "")
    temp_block = f"\nClima: {temp_line}\n" if temp_line else ""

    return f"""Você é uma consultora de moda experiente. A seguir estão as peças \
disponíveis no guarda-roupa da cliente — cada uma com a FOTO e os atributos, \
identificada por um id. Monte UM look coerente e bonito, escolhendo SOMENTE \
entre estas peças (referencie pelo id exato).

Contexto do look: {ctx_s}.
{temp_block}
{style_profile.prompt_fragment()}

OLHE AS FOTOS para julgar a cor real e a textura de cada peça (não confie só no \
rótulo de cor). Priorize as peças cujas cores realmente favorecem a coloração da \
cliente; evite as que a apagam.

Regras:
- Um item por slot do corpo. O look precisa de (vestido/macacão) OU (top + bottom), \
mais um calçado. Outerwear, bolsa e no máximo 1 acessório são opcionais.
- Respeite a ocasião, a estação e, sobretudo, o CLIMA (casaco no frio, nada de agasalho no calor).
- Se faltar algum slot essencial, monte com o que existe — NÃO invente peças nem \
use ids fora da lista.

Devolva os ids escolhidos e uma justificativa curta citando por que as cores \
funcionam para ela."""


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None)
        return code is None or code == 429 or code >= 500
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=20),
    reraise=True,
)
def _call_gemini(contents: list, model: str) -> StyledLook:
    client = get_gemini_client()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=StyledLook,
            temperature=0.7,
        ),
    )
    parsed = response.parsed
    if not isinstance(parsed, StyledLook):
        raise StylistError("Resposta do estilista não pôde ser parseada no schema.")
    return parsed


def style_look(candidates: list[dict], occasion=None, season=None, temperature=None) -> StyledLook:
    """Escolhe um look entre os candidatos (com visão). Lança StylistError em falha."""
    settings = get_settings()
    visual = candidates[:MAX_IMAGES]

    # baixa as imagens em paralelo (I/O) para não somar latências em série
    with ThreadPoolExecutor(max_workers=6) as pool:
        images = list(pool.map(lambda g: storage.download_image(g["id"]), visual))

    contents: list = [_instructions(occasion, season, temperature)]
    for g, img in zip(visual, images):
        if img:
            contents.append(f"id={g['id']} — {_facets(g)}:")
            contents.append(types.Part.from_bytes(data=img, mime_type="image/jpeg"))
        else:
            contents.append(f"id={g['id']} — {_facets(g)} (sem foto disponível).")

    try:
        return _call_gemini(contents, settings.gemini_model)
    except APIError as exc:
        raise StylistError(f"Erro da API Gemini: {exc}") from exc
