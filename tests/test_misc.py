"""Testes de embeddings (normalização/texto), perfil de estilo e schema."""

import math

from wardrobe import embeddings, schema, style_profile


def test_normalize_norma_unitaria():
    v = embeddings._normalize([3.0, 4.0])
    assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-9


def test_normalize_vetor_zero_nao_explode():
    assert embeddings._normalize([0.0, 0.0]) == [0.0, 0.0]


def test_garment_text_inclui_descricao_e_facetas():
    t = embeddings.garment_text(
        {
            "description": "blusa linda em tom vinho",
            "subcategory": "blusa",
            "primary_color": "vermelho",
            "material": None,
            "pattern": "liso",
            "formality": "casual",
            "seasons": ["inverno"],
            "occasions": [],
            "style_aesthetics": [],
            "brand": "Maison X",
        }
    )
    assert "blusa linda em tom vinho" in t
    assert "vermelho" in t
    assert "inverno" in t
    assert "Maison X" in t


def test_prompt_fragment_flexivel_e_inverno_disponivel():
    # Default agora é a paleta flexível (sem coloração fixa).
    f = style_profile.prompt_fragment().lower()
    assert "flexível" in f or "sem coloração fixa" in f
    assert "textura" in f
    # O conhecimento de inverno frio segue guardado, acessível por nome.
    inv = style_profile.prompt_fragment("inverno_frio").lower()
    assert "inverno frio" in inv
    assert "vinho" in inv or "bordô" in inv


def test_color_family_e_fechada_sem_vinho():
    vals = {c.value for c in schema.ColorFamily}
    assert "vermelho" in vals
    assert "vinho" not in vals  # "vinho" cai em vermelho/roxo — invariante do produto
