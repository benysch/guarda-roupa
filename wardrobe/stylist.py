"""
IA estilista: monta UM look escolhendo entre peças reais e explica o porquê,
aplicando o perfil de coloração da cliente (style_profile).

Híbrido: o motor de regras (looks.py) fornece os candidatos válidos (peças que
existem no acervo, sem categorias incompatíveis); aqui o Gemini exerce o "bom
gosto" — escolhe a combinação, prioriza as cores que favorecem e justifica.
Fica preso ao conjunto fornecido (referencia por id), então não inventa roupa.
"""

import logging

from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from . import style_profile
from .config import get_gemini_client, get_settings

logger = logging.getLogger(__name__)


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


def _candidate_block(candidates: list[dict]) -> str:
    lines = []
    for g in candidates:
        facets = [
            g.get("subcategory") or g.get("category"),
            g.get("primary_color"),
            g.get("material"),
            g.get("pattern"),
            g.get("formality"),
            g.get("brand"),
        ]
        attrs = ", ".join(str(f) for f in facets if f)
        desc = (g.get("description") or "")[:120]
        lines.append(f'- id={g["id"]} | {g["category"]} | {attrs} | {desc}')
    return "\n".join(lines)


def _build_prompt(candidates, occasion, season) -> str:
    ctx = []
    if occasion:
        ctx.append(f"ocasião: {occasion.replace('_', ' ')}")
    if season:
        ctx.append(f"estação: {season}")
    ctx_s = "; ".join(ctx) or "uso geral do dia a dia"

    return f"""Você é uma consultora de moda experiente. Monte UM look coerente e bonito \
para a cliente usando SOMENTE as peças da lista abaixo (referencie pelo id exato).

Contexto do look: {ctx_s}.

{style_profile.prompt_fragment()}

Regras:
- Um item por slot do corpo. O look precisa de (vestido/macacão) OU (top + bottom), \
mais um calçado. Outerwear, bolsa e no máximo 1 acessório são opcionais.
- Respeite a ocasião e a estação informadas.
- PRIORIZE as peças cujas cores mais favorecem a coloração da cliente; evite as que a apagam.
- Se faltar algum slot essencial no acervo, monte com o que existe — NÃO invente peças \
nem use ids que não estão na lista.

Peças disponíveis:
{_candidate_block(candidates)}

Devolva os ids escolhidos e uma justificativa curta citando por que as cores funcionam \
para ela."""


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
def _call_gemini(prompt: str) -> StyledLook:
    settings = get_settings()
    client = get_gemini_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
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


def style_look(candidates: list[dict], occasion=None, season=None) -> StyledLook:
    """Escolhe um look entre os candidatos. Lança StylistError em falha definitiva."""
    try:
        return _call_gemini(_build_prompt(candidates, occasion, season))
    except APIError as exc:
        raise StylistError(f"Erro da API Gemini: {exc}") from exc
