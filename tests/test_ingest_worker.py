"""Testes do worker de ingestão em segundo plano (IO mockado, sem rede)."""

from wardrobe import embeddings, ingest_worker, storage
from wardrobe.extractor import ExtractionError


class _Norm:
    def __init__(self, h="hash1", jpeg=b"jpeg"):
        self.content_hash = h
        self.jpeg_bytes = jpeg


class _Meta:
    def __init__(self, is_garment=True):
        self.is_garment = is_garment


class FakeTelegram:
    """Captura o que o worker mandaria pro Telegram."""

    def __init__(self, *_a, **_k):
        self.messages: list[tuple[int, str]] = []
        self.downloaded: list[str] = []

    def download_photo(self, file_id: str) -> bytes:
        self.downloaded.append(file_id)
        return b"raw-bytes"

    def send_message(self, chat_id: int, text: str, keyboard=None) -> None:
        self.messages.append((chat_id, text))


def _happy_path(monkeypatch, calls: dict):
    """Mocks para o caminho feliz COM IA; `calls` registra o que foi chamado."""
    monkeypatch.setattr(ingest_worker, "USE_AI", True)
    monkeypatch.setattr(ingest_worker, "normalize_image", lambda raw: _Norm())
    monkeypatch.setattr(ingest_worker, "extract_garment", lambda jpeg: _Meta(True))
    monkeypatch.setattr(storage, "find_existing_id", lambda h: None)
    monkeypatch.setattr(storage, "new_garment_id", lambda: "gid-1")
    monkeypatch.setattr(storage, "upload_image", lambda gid, jpeg: f"{gid}.jpg")

    def _insert(**kw):
        calls["insert"] = kw
        return kw["garment_id"]

    monkeypatch.setattr(storage, "insert_garment", _insert)
    monkeypatch.setattr(storage, "get_garment", lambda gid: {"id": gid})
    monkeypatch.setattr(embeddings, "garment_text", lambda g: "texto")
    monkeypatch.setattr(embeddings, "embed", lambda *a, **k: [0.0] * 768)
    monkeypatch.setattr(storage, "update_embedding", lambda gid, vec: None)

    def _finish(job_id, status, error=None):
        calls["finish"] = (job_id, status, error)

    monkeypatch.setattr(storage, "finish_ingest", _finish)


def test_process_one_insere_peca_processed(monkeypatch):
    calls: dict = {}
    _happy_path(monkeypatch, calls)
    tg = FakeTelegram()

    ingest_worker._process_one(tg, {"id": "job-1", "chat_id": 9, "file_id": "f1"})

    assert tg.downloaded == ["f1"]
    assert calls["insert"]["status"] == "processed"
    assert calls["insert"]["garment_id"] == "gid-1"
    assert calls["finish"] == ("job-1", "done", None)


def test_process_one_bare_sem_ia(monkeypatch):
    """Com IA desligada, sobe a peça CRUA (needs_review) sem chamar o Gemini."""
    monkeypatch.setattr(ingest_worker, "USE_AI", False)
    monkeypatch.setattr(ingest_worker, "normalize_image", lambda raw: _Norm())
    monkeypatch.setattr(storage, "find_existing_id", lambda h: None)
    monkeypatch.setattr(storage, "new_garment_id", lambda: "gid-bare")
    monkeypatch.setattr(storage, "upload_image", lambda gid, jpeg: f"{gid}.jpg")

    def _no_extract(jpeg):
        raise AssertionError("não deve chamar a IA com USE_AI desligado")

    monkeypatch.setattr(ingest_worker, "extract_garment", _no_extract)

    bare: dict = {}
    monkeypatch.setattr(
        storage,
        "insert_bare_garment",
        lambda **kw: bare.update(kw) or kw["garment_id"],
    )
    finished: dict = {}
    monkeypatch.setattr(
        storage, "finish_ingest", lambda jid, st, err=None: finished.update(id=jid, st=st)
    )
    tg = FakeTelegram()

    ingest_worker._process_one(tg, {"id": "job-b", "chat_id": 9, "file_id": "fb"})
    assert bare["garment_id"] == "gid-bare"
    assert bare["status"] == "needs_review"
    assert finished == {"id": "job-b", "st": "done"}


def test_process_one_duplicata_nao_insere(monkeypatch):
    calls: dict = {}
    _happy_path(monkeypatch, calls)
    monkeypatch.setattr(storage, "find_existing_id", lambda h: "existente")

    def _boom(**kw):
        raise AssertionError("não deveria inserir duplicata")

    monkeypatch.setattr(storage, "insert_garment", _boom)
    tg = FakeTelegram()

    ingest_worker._process_one(tg, {"id": "job-2", "chat_id": 9, "file_id": "f2"})
    assert calls["finish"] == ("job-2", "done", None)


def test_process_one_nao_roupa_falha(monkeypatch):
    calls: dict = {}
    _happy_path(monkeypatch, calls)
    monkeypatch.setattr(ingest_worker, "extract_garment", lambda jpeg: _Meta(False))
    tg = FakeTelegram()

    ingest_worker._process_one(tg, {"id": "job-3", "chat_id": 9, "file_id": "f3"})
    assert calls["finish"][1] == "failed"
    assert "insert" not in calls


def test_process_one_extracao_falha(monkeypatch):
    calls: dict = {}
    _happy_path(monkeypatch, calls)

    def _boom(jpeg):
        raise ExtractionError("ia fora do ar")

    monkeypatch.setattr(ingest_worker, "extract_garment", _boom)
    tg = FakeTelegram()

    ingest_worker._process_one(tg, {"id": "job-4", "chat_id": 9, "file_id": "f4"})
    assert calls["finish"][1] == "failed"


def test_process_one_429_reenfileira_nao_falha(monkeypatch):
    calls: dict = {}
    _happy_path(monkeypatch, calls)

    def _boom(jpeg):
        raise ExtractionError(
            "Erro da API Gemini: 429 RESOURCE_EXHAUSTED. quota exceeded"
        )

    monkeypatch.setattr(ingest_worker, "extract_garment", _boom)

    requeued: dict = {}
    monkeypatch.setattr(
        storage, "requeue_ingest", lambda jid, note=None: requeued.update(id=jid, note=note)
    )

    def _no_finish(*a, **k):
        raise AssertionError("não deve marcar failed num 429 transitório")

    monkeypatch.setattr(storage, "finish_ingest", _no_finish)
    tg = FakeTelegram()

    ingest_worker._process_one(tg, {"id": "job-9", "chat_id": 9, "file_id": "f9"})
    assert requeued["id"] == "job-9"


def test_is_transient():
    assert ingest_worker._is_transient("429 RESOURCE_EXHAUSTED")
    assert ingest_worker._is_transient("503 UNAVAILABLE")
    assert not ingest_worker._is_transient("Resposta não pôde ser parseada no schema")


def test_maybe_notify_resume_quando_esvazia(monkeypatch):
    monkeypatch.setattr(storage, "chat_has_open_jobs", lambda c: False)
    monkeypatch.setattr(
        storage,
        "unnotified_results",
        lambda c: [
            {"id": "a", "status": "done"},
            {"id": "b", "status": "done"},
            {"id": "c", "status": "failed"},
        ],
    )
    marked: dict = {}
    monkeypatch.setattr(storage, "mark_notified", lambda ids: marked.update(ids=ids))
    tg = FakeTelegram()

    ingest_worker._maybe_notify(tg, 9)

    assert len(tg.messages) == 1
    _, text = tg.messages[0]
    assert "2 fotos no site" in text  # modo sem-IA (padrão): prontas pra classificar
    assert "1 ignorada" in text
    assert "A classificar" in text
    assert marked["ids"] == ["a", "b", "c"]


def test_maybe_notify_silencia_com_fila_aberta(monkeypatch):
    monkeypatch.setattr(storage, "chat_has_open_jobs", lambda c: True)
    tg = FakeTelegram()
    ingest_worker._maybe_notify(tg, 9)
    assert tg.messages == []


def test_process_pending_reivindica_e_avisa(monkeypatch):
    calls: dict = {}
    _happy_path(monkeypatch, calls)
    monkeypatch.setattr(ingest_worker, "Telegram", FakeTelegram)
    monkeypatch.setattr(
        ingest_worker, "get_settings", lambda: type("S", (), {"telegram_bot_token": "t"})()
    )
    monkeypatch.setattr(
        storage, "claim_ingest_jobs", lambda n: [{"id": "j", "chat_id": 9, "file_id": "f"}]
    )
    monkeypatch.setattr(storage, "chat_has_open_jobs", lambda c: False)
    monkeypatch.setattr(
        storage, "unnotified_results", lambda c: [{"id": "j", "status": "done"}]
    )
    monkeypatch.setattr(storage, "mark_notified", lambda ids: None)

    out = ingest_worker.process_pending()
    assert out == {"claimed": 1}
    assert calls["finish"] == ("j", "done", None)
