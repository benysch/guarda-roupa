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


def test_pack_capsule_shape(monkeypatch):
    monkeypatch.setattr(storage, "fetch_garments", lambda *a, **k: WARDROBE)

    out = webapi.pack_capsule("2", "dia", "", "")
    assert out["days"] == 2
    assert out["occasion"] == "dia_a_dia"
    assert out["night"] is None
    assert len(out["looks"]) == 2  # sem noite: 1 slot por dia
    assert out["looks"][0]["label"] == "Dia 1"
    # acervo de 1 top/1 bottom/1 calçado -> a mala reusa as mesmas 3 peças
    assert out["total"] == 3
    cats = [grp["category"] for grp in out["groups"]]
    assert cats == ["top", "bottom", "footwear"]


def test_pack_capsule_noite_dobra_slots(monkeypatch):
    monkeypatch.setattr(storage, "fetch_garments", lambda *a, **k: WARDROBE)

    out = webapi.pack_capsule("2", "dia", "encontro", "")
    assert out["night"] == "encontro"
    assert [sl["label"] for sl in out["looks"]] == [
        "Dia 1",
        "Dia 1 — noite",
        "Dia 2",
        "Dia 2 — noite",
    ]


def test_pack_capsule_days_invalido_usa_default(monkeypatch):
    monkeypatch.setattr(storage, "fetch_garments", lambda *a, **k: WARDROBE)

    out = webapi.pack_capsule("abc", "", "", "")
    assert out["days"] == 3
    out = webapi.pack_capsule("99", "", "", "")
    assert out["days"] == 14  # clamp


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
