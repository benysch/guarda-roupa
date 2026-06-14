"""Testes da engine de mala de viagem (lógica pura)."""

from wardrobe import capsule
from wardrobe.capsule import TripSlot


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


TRABALHO_3_DIAS = [
    TripSlot("seg — trabalho", occasion="trabalho"),
    TripSlot("ter — trabalho", occasion="trabalho"),
    TripSlot("qua — trabalho", occasion="trabalho"),
]


def acervo_trabalho():
    return [
        g(id="t1", category="top", primary_color="branco", formality="trabalho"),
        g(id="t2", category="top", primary_color="cinza", formality="trabalho"),
        g(id="t3", category="top", primary_color="rosa", formality="trabalho"),
        g(id="b1", category="bottom", primary_color="preto", formality="trabalho"),
        g(id="b2", category="bottom", primary_color="cinza", formality="trabalho"),
        g(id="s1", category="footwear", primary_color="preto", formality="trabalho"),
    ]


def test_reusa_base_e_roda_camada_visivel():
    cap = capsule.pack(acervo_trabalho(), TRABALHO_3_DIAS, include_bag=False)
    # Mala mínima: 1 bottom e 1 calçado reusados em todos os dias.
    bottoms = [p for p in cap.pieces if p["category"] == "bottom"]
    shoes = [p for p in cap.pieces if p["category"] == "footwear"]
    assert len(bottoms) == 1 and len(shoes) == 1
    # Camada visível roda: nenhum dia repete o top do dia anterior.
    tops_por_dia = [
        next(p["id"] for p in sl.pieces if p["category"] == "top") for sl in cap.looks
    ]
    for ontem, hoje in zip(tops_por_dia, tops_por_dia[1:]):
        assert ontem != hoje
    # E ainda assim a mala não leva top à toa: 2 tops alternados bastam p/ 3 dias.
    assert len([p for p in cap.pieces if p["category"] == "top"]) == 2
    assert all(not sl.missing for sl in cap.looks)


def test_full_body_cobre_slot_sem_top_bottom():
    acervo = [
        g(id="v1", category="full_body", formality="cocktail"),
        g(id="s1", category="footwear", formality="cocktail"),
    ]
    cap = capsule.pack(acervo, [TripSlot("sáb — festa", occasion="festa")])
    cats = {p["category"] for p in cap.looks[0].pieces}
    assert "full_body" in cats and "footwear" in cats
    assert cap.looks[0].missing == []


def test_slot_descoberto_alimenta_gap_analysis():
    acervo = [g(id="t1", category="top"), g(id="b1", category="bottom")]
    cap = capsule.pack(acervo, [TripSlot("dom — passeio")])
    assert cap.looks[0].missing == ["footwear"]
    assert cap.uncovered == [cap.looks[0]]


def test_estacao_filtra_pecas_e_pede_casaco():
    acervo = acervo_trabalho() + [
        g(id="o1", category="outerwear", primary_color="preto",
          formality="trabalho", seasons=["inverno"]),
        g(id="t9", category="top", primary_color="branco",
          formality="trabalho", seasons=["verao"]),
    ]
    frio = [TripSlot("seg — trabalho", occasion="trabalho", season="inverno")]
    cap = capsule.pack(acervo, frio, include_bag=False)
    cats = {p["category"] for p in cap.looks[0].pieces}
    assert "outerwear" in cats  # clima frio empacota casaco
    ids = {p["id"] for p in cap.pieces}
    assert "t9" not in ids  # peça de verão fica em casa


def test_paleta_flexivel_aceita_tom_quente():
    # Paleta flexível: bege (tom quente) não é demovido — entra normalmente.
    acervo = [
        g(id="tb", category="top", primary_color="bege"),
        g(id="b1", category="bottom"),
        g(id="s1", category="footwear"),
    ]
    cap = capsule.pack(acervo, [TripSlot("seg")], include_bag=False)
    top = next(p for p in cap.looks[0].pieces if p["category"] == "top")
    assert top["id"] == "tb"


def test_harmonia_de_cor_no_look():
    acervo = [
        g(id="t1", category="top", primary_color="vermelho"),
        g(id="bz", category="bottom", primary_color="azul"),
        g(id="bp", category="bottom", primary_color="preto"),
        g(id="s1", category="footwear"),
    ]
    cap = capsule.pack(acervo, [TripSlot("seg")], include_bag=False)
    bottom = next(p for p in cap.looks[0].pieces if p["category"] == "bottom")
    assert bottom["id"] == "bp"  # duas statements diferentes não convivem


def test_uma_bolsa_para_a_viagem():
    acervo = acervo_trabalho() + [
        g(id="g1", category="bag", primary_color="preto"),
        g(id="g2", category="bag", primary_color="vermelho"),
    ]
    cap = capsule.pack(acervo, TRABALHO_3_DIAS, include_bag=True)
    bags = [p for p in cap.pieces if p["category"] == "bag"]
    assert [b["id"] for b in bags] == ["g1"]  # uma só, e neutra


def test_by_category_agrupa_na_ordem():
    cap = capsule.pack(acervo_trabalho(), TRABALHO_3_DIAS, include_bag=False)
    grupos = cap.by_category()
    assert list(grupos.keys()) == ["top", "bottom", "footwear"]
