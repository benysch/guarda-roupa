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
