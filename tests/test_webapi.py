"""Testes dos endpoints do cérebro (webapi) com IO mockado (sem rede)."""

from wardrobe import storage, stylist, webapi


def _g(gid, category, **kw):
    base = dict(
        id=gid,
        category=category,
        subcategory=None,
        primary_color="preto",
        material=None,
        pattern="liso",
        formality="casual",
        brand=None,
        description="desc",
        seasons=[],
        occasions=[],
    )
    base.update(kw)
    return base


WARDROBE = [
    _g("a", "top"),
    _g("b", "bottom"),
    _g("c", "footwear"),
]


def test_compose_look_usa_estilista(monkeypatch):
    monkeypatch.setattr(storage, "fetch_garments", lambda *a, **k: WARDROBE)

    class SL:
        garment_ids = ["a", "b", "c"]
        rationale = "porque as cores são frias"

    monkeypatch.setattr(stylist, "style_look", lambda *a, **k: SL())

    out = webapi.compose_look("dia", "")
    assert [p["id"] for p in out["pieces"]] == ["a", "b", "c"]
    assert out["rationale"] == "porque as cores são frias"
    assert out["missing"] == []
    assert out["occasion"] == "dia_a_dia"


def test_compose_look_fallback_quando_estilista_falha(monkeypatch):
    monkeypatch.setattr(storage, "fetch_garments", lambda *a, **k: WARDROBE)

    def boom(*a, **k):
        raise RuntimeError("gemini fora do ar")

    monkeypatch.setattr(stylist, "style_look", boom)

    out = webapi.compose_look("dia", "")
    assert len(out["pieces"]) >= 1  # motor de regras assume
    assert out["rationale"] is None


def test_compose_look_ignora_ids_invalidos_do_estilista(monkeypatch):
    monkeypatch.setattr(storage, "fetch_garments", lambda *a, **k: WARDROBE)

    class SL:
        garment_ids = ["a", "inexistente"]
        rationale = "x"

    monkeypatch.setattr(stylist, "style_look", lambda *a, **k: SL())
    out = webapi.compose_look("dia", "")
    ids = {p["id"] for p in out["pieces"]}
    assert "inexistente" not in ids
    assert "a" in ids


def test_pack_capsule_monta_mala_e_looks_por_dia(monkeypatch):
    import json

    acervo = [
        _g("t1", "top", primary_color="branco", formality="trabalho"),
        _g("t2", "top", primary_color="cinza", formality="trabalho"),
        _g("b1", "bottom", primary_color="preto", formality="trabalho"),
        _g("s1", "footwear", primary_color="preto", formality="trabalho"),
    ]
    monkeypatch.setattr(storage, "fetch_garments", lambda *a, **k: acervo)

    trip = json.dumps(
        [
            {"season": "", "occasions": ["trabalho", "trabalho"]},
            {"season": "", "occasions": ["trabalho"]},
        ]
    )
    out = webapi.pack_capsule(trip, include_bag=False)

    # dois dias, com 2 e 1 looks respectivamente
    assert [len(d["looks"]) for d in out["days"]] == [2, 1]
    # a mala é mínima: 1 bottom e 1 calçado reusados, sem faltas
    assert {p["id"] for p in out["suitcase"]["bottom"]} == {"b1"}
    assert {p["id"] for p in out["suitcase"]["footwear"]} == {"s1"}
    assert out["uncovered"] == []
    # cada look traz o shape de peça esperado pelo site
    primeiro = out["days"][0]["looks"][0]
    assert primeiro["occasion"] == "trabalho"
    assert set(primeiro["pieces"][0]) == {
        "id", "category", "subcategory", "primary_color", "brand", "description"
    }


def test_pack_capsule_reporta_lacuna(monkeypatch):
    import json

    monkeypatch.setattr(
        storage, "fetch_garments", lambda *a, **k: [_g("t1", "top"), _g("b1", "bottom")]
    )
    out = webapi.pack_capsule(json.dumps([{"occasions": ["dia"]}]))
    assert out["uncovered"] and out["uncovered"][0]["missing"] == ["footwear"]


def test_search_shape(monkeypatch):
    monkeypatch.setattr(webapi.embeddings, "embed", lambda *a, **k: [0.1] * 768)
    monkeypatch.setattr(
        storage,
        "match_garments",
        lambda vec, match_count=8: [
            {
                "id": "a",
                "category": "top",
                "subcategory": "blusa",
                "primary_color": "preto",
                "brand": None,
                "description": "d",
                "similarity": 0.9,
            }
        ],
    )
    out = webapi.search("blusa preta", 5)
    assert out["query"] == "blusa preta"
    assert out["results"][0]["id"] == "a"
    assert out["results"][0]["similarity"] == 0.9


def test_search_query_vazia_nao_chama_embed(monkeypatch):
    def nope(*a, **k):
        raise AssertionError("não deveria embeddar query vazia")

    monkeypatch.setattr(webapi.embeddings, "embed", nope)
    out = webapi.search("", 5)
    assert out["results"] == []


def test_similar_shape(monkeypatch):
    monkeypatch.setattr(
        storage,
        "similar_garments",
        lambda gid, k=6: [
            {
                "id": "b",
                "category": "top",
                "subcategory": None,
                "primary_color": "azul",
                "brand": None,
                "description": None,
                "similarity": 0.82,
            }
        ],
    )
    out = webapi.similar("a", 4)
    assert out["id"] == "a"
    assert out["results"][0]["id"] == "b"
    assert out["results"][0]["similarity"] == 0.82
