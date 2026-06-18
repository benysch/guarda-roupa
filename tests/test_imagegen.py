"""Testes da geração de imagem do look (Gemini mockado — sem rede)."""

import types as pytypes

import pytest

from wardrobe import imagegen, storage


def _fake_client(png: bytes):
    part = pytypes.SimpleNamespace(inline_data=pytypes.SimpleNamespace(data=png))
    candidate = pytypes.SimpleNamespace(
        content=pytypes.SimpleNamespace(parts=[part])
    )
    resp = pytypes.SimpleNamespace(candidates=[candidate])

    class Models:
        def generate_content(self, **kwargs):
            return resp

    return pytypes.SimpleNamespace(models=Models())


def test_gera_png(monkeypatch):
    monkeypatch.setattr(storage, "download_image", lambda gid: b"\xff\xd8jpeg")
    monkeypatch.setattr(imagegen, "_collage", lambda imgs: b"collage")
    monkeypatch.setattr(imagegen, "get_gemini_client", lambda: _fake_client(b"PNGBYTES"))
    out = imagegen.generate_look_image(["a", "b"], "festa", "inverno")
    assert out == b"PNGBYTES"


def test_429_vira_quota_error(monkeypatch):
    monkeypatch.setattr(storage, "download_image", lambda gid: b"x")
    monkeypatch.setattr(imagegen, "_collage", lambda imgs: b"collage")

    class Models:
        def generate_content(self, **kwargs):
            raise RuntimeError("429 RESOURCE_EXHAUSTED: check your plan and billing")

    monkeypatch.setattr(
        imagegen, "get_gemini_client", lambda: pytypes.SimpleNamespace(models=Models())
    )
    with pytest.raises(imagegen.QuotaError):
        imagegen.generate_look_image(["a"])


def test_sem_fotos_levanta_erro(monkeypatch):
    monkeypatch.setattr(storage, "download_image", lambda gid: None)
    with pytest.raises(imagegen.ImageGenError):
        imagegen.generate_look_image(["a"])


def test_resposta_sem_imagem_levanta_erro(monkeypatch):
    monkeypatch.setattr(storage, "download_image", lambda gid: b"x")
    monkeypatch.setattr(imagegen, "_collage", lambda imgs: b"collage")
    empty = pytypes.SimpleNamespace(
        candidates=[
            pytypes.SimpleNamespace(content=pytypes.SimpleNamespace(parts=[]))
        ]
    )

    class Models:
        def generate_content(self, **kwargs):
            return empty

    monkeypatch.setattr(
        imagegen, "get_gemini_client", lambda: pytypes.SimpleNamespace(models=Models())
    )
    with pytest.raises(imagegen.ImageGenError):
        imagegen.generate_look_image(["a"])
