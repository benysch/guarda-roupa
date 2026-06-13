"""Testes do miolo PURO do recorte (sem rembg/onnx — só PIL).

cutout_garment() depende do rembg (extra local-only); aqui testamos o que
não precisa do modelo: gating de categoria, seleção da faixa e crop no bbox.
"""

import io

from PIL import Image

from wardrobe import cutout


def _rgba(w, h, boxes):
    """Imagem RGBA transparente com retângulos opacos (x0,y0,x1,y1)."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for (x0, y0, x1, y1) in boxes:
        for x in range(x0, x1):
            for y in range(y0, y1):
                px[x, y] = (120, 120, 120, 255)
    return img


def test_should_cutout_gating():
    assert cutout.should_cutout("top")
    assert cutout.should_cutout("outerwear")
    assert cutout.should_cutout("hosiery")
    # nunca recorta bolsa/acessório (cloth_seg falha nelas)
    assert not cutout.should_cutout("bag")
    assert not cutout.should_cutout("accessory")
    assert not cutout.should_cutout(None)


def test_best_band_escolhe_faixa_de_maior_area():
    # 3 faixas de 30px; peça grande na faixa do meio, ruído pequeno na primeira
    img = _rgba(30, 90, [(0, 0, 5, 5), (2, 35, 28, 58)])
    band = cutout._best_band(img)
    assert band is not None
    assert band.size == (30, 30)  # uma faixa
    # a faixa escolhida (meio) tem muito mais pixel opaco que a primeira
    opaque = sum(1 for a in band.getchannel("A").getdata() if a > 10)
    assert opaque > 100


def test_best_band_none_quando_tudo_transparente():
    assert cutout._best_band(_rgba(30, 90, [])) is None


def test_crop_to_content_recorta_no_bbox_com_margem():
    band = _rgba(100, 100, [(40, 40, 60, 60)])
    cropped = cutout._crop_to_content(band)
    assert cropped is not None
    # 20px de peça + margem (4% de 100 = 4px) dos dois lados -> ~28px
    assert 26 <= cropped.size[0] <= 30
    assert 26 <= cropped.size[1] <= 30


def test_crop_to_content_none_quando_vazio():
    assert cutout._crop_to_content(_rgba(50, 50, [])) is None
