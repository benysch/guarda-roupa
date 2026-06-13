"""Testes da engine de composição de looks (lógica pura)."""

import random

from wardrobe import looks


def g(**kw):
    base = dict(
        id="x",
        category="top",
        primary_color="preto",
        formality="casual",
        seasons=[],
        occasions=[],
    )
    base.update(kw)
    return base


def test_parse_occasion_alias_e_substring():
    assert looks.parse_occasion("quero algo de festa hoje") == "festa"
    assert looks.parse_occasion("dia") == "dia_a_dia"
    assert looks.parse_occasion("") is None
    assert looks.parse_occasion("nada reconhecível") is None


def test_parse_season():
    assert looks.parse_season("um look de inverno") == "inverno"
    assert looks.parse_season("verão na praia") == "verao"
    assert looks.parse_season("") is None


def test_missing_slots():
    assert looks.missing_slots([g(category="top")]) == ["bottom", "footwear"]
    assert looks.missing_slots([g(category="full_body"), g(category="footwear")]) == []
    completo = [g(category="top"), g(category="bottom"), g(category="footwear")]
    assert looks.missing_slots(completo) == []


def test_candidates_exclui_grupos_intimos():
    garments = [
        g(category="top"),
        g(category="lingerie"),
        g(category="sleepwear"),
        g(category="beachwear"),
    ]
    cats = {x["category"] for x in looks.candidates(garments)}
    assert cats == {"top"}


def test_candidates_beachwear_liberado_na_praia():
    assert len(looks.candidates([g(category="beachwear")], occasion="praia")) == 1


def test_candidates_prioriza_ocasiao():
    a = g(id="a", occasions=["festa"])
    b = g(id="b", occasions=[])
    out = looks.candidates([b, a], occasion="festa")
    assert out[0]["id"] == "a"


def test_color_ok():
    assert looks._color_ok(["vermelho"], "preto") is True  # neutro entra sempre
    assert looks._color_ok(["vermelho"], "vermelho") is True  # mesma statement
    assert looks._color_ok(["vermelho"], "azul") is False  # 2 statements diferentes


def test_formality_ok():
    cocktail = looks.FORMALITY_RANK["cocktail"]
    assert looks._formality_ok(cocktail, g(formality="trabalho")) is True  # adjacente
    assert looks._formality_ok(cocktail, g(formality="casual")) is False  # 3 níveis
    assert looks._formality_ok(None, g(formality="casual")) is True  # sem alvo


def test_season_ok():
    assert looks._season_ok(g(seasons=[]), "inverno") is True  # atemporal
    assert looks._season_ok(g(seasons=["inverno"]), "inverno") is True
    assert looks._season_ok(g(seasons=["verao"]), "inverno") is False


def test_compose_acervo_completo():
    wardrobe = [
        g(id="t", category="top"),
        g(id="b", category="bottom"),
        g(id="f", category="footwear"),
    ]
    look = looks.compose(wardrobe, rng=random.Random(0))
    cats = {p["category"] for p in look.pieces}
    assert {"top", "bottom", "footwear"} <= cats
    assert look.complete is True


def test_compose_acervo_vazio():
    look = looks.compose([])
    assert look.pieces == []
    assert set(look.missing) == {"top", "bottom", "footwear"}


def test_neutrals_sao_da_paleta():
    # Inverno frio: bege/marrom/dourado NÃO são neutros (lista 'evita' do perfil).
    assert "bege" not in looks.NEUTRALS
    assert "marrom" not in looks.NEUTRALS
    assert "dourado" not in looks.NEUTRALS
    # Neutros frios permanecem.
    assert {"preto", "branco", "cinza", "prateado"} <= looks.NEUTRALS


def test_color_ok_bege_e_statement():
    # Com uma statement já no look, bege não entra mais como neutro universal.
    assert looks._color_ok(["vermelho"], "bege") is False


def test_cands_demove_cor_evita():
    base = {"formality": "casual", "seasons": [], "occasions": []}
    bege = {"id": "1", "category": "top", "primary_color": "bege", **base}
    branco = {"id": "2", "category": "top", "primary_color": "branco", **base}
    hits = looks._cands([[bege, branco]], "top", None, None, [])
    assert hits == [branco]  # bege demovida quando há alternativa
    hits = looks._cands([[bege]], "top", None, None, [])
    assert hits == [bege]  # mas não bloqueada quando é a única opção


# --------------------------------------------------------------------------- #
# Temperatura
# --------------------------------------------------------------------------- #
def test_parse_temperature():
    assert looks.parse_temperature("um look pra hoje, tá frio") == "frio"
    assert looks.parse_temperature("calor demais") == "quente"
    assert looks.parse_temperature("festa") is None


def test_temp_from_celsius():
    assert looks.temp_from_celsius(8) == "frio"
    assert looks.temp_from_celsius(14.9) == "frio"
    assert looks.temp_from_celsius(20) == "ameno"
    assert looks.temp_from_celsius(28) == "quente"


def test_wants_outerwear():
    rng = random.Random(0)
    assert looks.wants_outerwear("frio", None, rng) is True
    assert looks.wants_outerwear("quente", "inverno", rng) is False  # calor manda


def test_compose_frio_inclui_casaco():
    wardrobe = [
        g(id="t", category="top"),
        g(id="b", category="bottom"),
        g(id="f", category="footwear"),
        g(id="c", category="outerwear"),
    ]
    look = looks.compose(wardrobe, temperature="frio", rng=random.Random(0))
    assert "outerwear" in {p["category"] for p in look.pieces}
    assert look.temperature == "frio"


def test_compose_quente_exclui_casaco():
    wardrobe = [
        g(id="t", category="top"),
        g(id="b", category="bottom"),
        g(id="f", category="footwear"),
        g(id="c", category="outerwear"),
    ]
    # Em qualquer semente, calor não veste casaco.
    for seed in range(5):
        look = looks.compose(wardrobe, temperature="quente", rng=random.Random(seed))
        assert "outerwear" not in {p["category"] for p in look.pieces}


def test_cands_prefere_material_quente_no_frio():
    base = {"category": "top", "primary_color": "preto", "formality": "casual",
            "seasons": [], "occasions": []}
    la = {"id": "1", "material": "la", **base}
    linho = {"id": "2", "material": "linho", **base}
    assert looks._cands([[linho, la]], "top", None, None, [], "frio") == [la]
    assert looks._cands([[linho, la]], "top", None, None, [], "quente") == [linho]


def test_cold_without_coat():
    com_casaco = [g(category="top"), g(category="outerwear")]
    sem_casaco = [g(category="top"), g(category="footwear")]
    assert looks.cold_without_coat(sem_casaco, "frio") is True
    assert looks.cold_without_coat(com_casaco, "frio") is False
    assert looks.cold_without_coat(sem_casaco, "quente") is False  # só alerta no frio
