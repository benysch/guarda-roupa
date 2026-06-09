"""
Embeddings para busca semântica.

Gera vetores 768-d com o Gemini (`gemini-embedding-001`) a partir de um texto
canônico da peça (descrição + atributos). O vetor vem NÃO-normalizado quando se
usa dimensão truncada (768 < 3072 nativo), então normalizamos para norma 1 —
requisito para a distância de cosseno do pgvector se comportar bem.

Camada fina e reaproveitável: não conhece Telegram nem Postgres.
"""

import math
import os

from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .config import get_gemini_client

EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = 768

# Tarefas do Gemini: documentos (acervo) e consultas (busca) usam tipos distintos.
TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"
TASK_QUERY = "RETRIEVAL_QUERY"


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def garment_text(g: dict) -> str:
    """Texto canônico de uma peça (linha do Postgres) para gerar o embedding."""
    parts: list[str] = []
    if g.get("description"):
        parts.append(g["description"])
    facets = [
        g.get("subcategory") or g.get("category"),
        g.get("primary_color"),
        g.get("material"),
        g.get("pattern"),
        g.get("formality"),
    ]
    facet_str = ", ".join(f for f in facets if f)
    if facet_str:
        parts.append(facet_str)
    for key in ("seasons", "occasions", "style_aesthetics"):
        vals = g.get(key) or []
        if vals:
            parts.append(", ".join(vals))
    if g.get("brand"):
        parts.append(str(g["brand"]))
    return ". ".join(parts)


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=15), reraise=True)
def embed(text: str, task_type: str = TASK_DOCUMENT) -> list[float]:
    """Gera o embedding normalizado (norma 1) de um texto."""
    from google.genai import types

    client = get_gemini_client()
    resp = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=EMBED_DIM
        ),
    )
    return _normalize(list(resp.embeddings[0].values))
