"""
Bot do Telegram (webhook serverless) para ingestão conversacional do guarda-roupa.

Fluxo: a Muri manda a foto -> o bot processa com a IA, salva a peça e puxa uma
conversa para confirmar a categoria e capturar marca/modelo (que a foto raramente
revela). Reaproveita imaging/extractor/storage; só a camada Telegram é nova.

Como é serverless (stateless entre mensagens), o estado da conversa vive na tabela
`telegram_sessions` (chat_id -> garment_id + step).
"""

import logging
import random

import httpx

from . import embeddings, looks, storage
from .config import get_settings, get_supabase_client
from .extractor import ExtractionError, extract_garment
from .imaging import ImageValidationError, normalize_image
from .schema import Category, ColorFamily, Material, Pattern

logger = logging.getLogger(__name__)

_API = "https://api.telegram.org/bot{token}/{method}"
_FILE = "https://api.telegram.org/file/bot{token}/{path}"

# Rótulos amigáveis das categorias para os botões de correção.
CATEGORY_LABELS: dict[str, str] = {
    "top": "👚 Top",
    "bottom": "👖 Bottom",
    "full_body": "👗 Vestido/Macacão",
    "outerwear": "🧥 Casaco",
    "footwear": "👠 Calçado",
    "bag": "👜 Bolsa",
    "accessory": "💍 Acessório",
    "hosiery": "🧦 Meias",
    "lingerie": "🩲 Lingerie",
    "sleepwear": "🌙 Pijama",
    "beachwear": "👙 Praia",
}

SESSIONS = "telegram_sessions"

# Campos corrigíveis no menu "✏️ Corrigir" -> (coluna no Postgres, Enum do vocabulário).
# A categoria reaproveita os rótulos com emoji acima; os demais geram rótulos do próprio Enum.
FIELD_ENUMS: dict[str, tuple[str, type]] = {
    "category": ("category", Category),
    "color": ("primary_color", ColorFamily),
    "pattern": ("pattern", Pattern),
    "material": ("material", Material),
}
EDIT_FIELDS = [
    ("category", "🏷️ Categoria"),
    ("color", "🎨 Cor"),
    ("pattern", "🔳 Estampa"),
    ("material", "🧵 Material"),
]


def _pretty(value: str) -> str:
    return value.replace("_", " ").capitalize()


def _chunk(items: list, n: int) -> list[list]:
    return [items[i : i + n] for i in range(0, len(items), n)]


def _value_keyboard(field: str) -> list[list[dict]]:
    """Botões com os valores possíveis do campo (3 por linha) + Voltar."""
    _, enum = FIELD_ENUMS[field]
    labels = CATEGORY_LABELS if field == "category" else {}
    btns = [
        {"text": labels.get(e.value, _pretty(e.value)), "callback_data": f"v:{field}:{e.value}"}
        for e in enum
    ]
    rows = _chunk(btns, 3)
    rows.append([{"text": "↩️ Voltar", "callback_data": "edit"}])
    return rows


# --------------------------------------------------------------------------- #
# Cliente Telegram (httpx síncrono — combina com o handler serverless)
# --------------------------------------------------------------------------- #
class Telegram:
    def __init__(self, token: str):
        self.token = token
        self.http = httpx.Client(timeout=30.0)

    def _call(self, method: str, payload: dict) -> dict:
        url = _API.format(token=self.token, method=method)
        r = self.http.post(url, json=payload)
        if r.status_code >= 400:
            logger.error("Telegram %s falhou: %s %s", method, r.status_code, r.text)
        return r.json() if r.content else {}

    def send_message(self, chat_id: int, text: str, keyboard: list | None = None) -> None:
        payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if keyboard:
            payload["reply_markup"] = {"inline_keyboard": keyboard}
        self._call("sendMessage", payload)

    def send_photo(self, chat_id: int, photo_url: str, caption: str | None = None) -> None:
        payload: dict = {"chat_id": chat_id, "photo": photo_url}
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "Markdown"
        self._call("sendPhoto", payload)

    def send_media_group(self, chat_id: int, photo_urls: list[str], caption: str | None = None) -> None:
        """Envia 2..10 fotos como álbum; a legenda vai na primeira."""
        media = []
        for i, url in enumerate(photo_urls):
            item: dict = {"type": "photo", "media": url}
            if i == 0 and caption:
                item["caption"] = caption
                item["parse_mode"] = "Markdown"
            media.append(item)
        self._call("sendMediaGroup", {"chat_id": chat_id, "media": media})

    def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
        self._call("answerCallbackQuery", payload)

    def react(self, chat_id: int, message_id: int, emoji: str = "👍") -> None:
        """Reage a uma mensagem (best-effort) — confirma sem poluir o chat com texto."""
        self._call(
            "setMessageReaction",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "reaction": [{"type": "emoji", "emoji": emoji}],
            },
        )

    def download_photo(self, file_id: str) -> bytes:
        info = self._call("getFile", {"file_id": file_id})
        path = info["result"]["file_path"]
        url = _FILE.format(token=self.token, path=path)
        return self.http.get(url).content


# --------------------------------------------------------------------------- #
# Sessão (estado da conversa)
# --------------------------------------------------------------------------- #
def _get_session(chat_id: int) -> dict | None:
    sb = get_supabase_client()
    resp = sb.table(SESSIONS).select("*").eq("chat_id", chat_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def _set_session(chat_id: int, garment_id: str, step: str) -> None:
    sb = get_supabase_client()
    sb.table(SESSIONS).upsert(
        {"chat_id": chat_id, "garment_id": garment_id, "step": step}
    ).execute()


def _clear_session(chat_id: int) -> None:
    sb = get_supabase_client()
    sb.table(SESSIONS).delete().eq("chat_id", chat_id).execute()


# --------------------------------------------------------------------------- #
# Formatação
# --------------------------------------------------------------------------- #
def _summary(g: dict) -> str:
    bits = [f"*{(g.get('subcategory') or g['category']).replace('_', ' ').title()}*"]
    label = CATEGORY_LABELS.get(g["category"], g["category"])
    parts = [label]
    if g.get("primary_color"):
        parts.append(g["primary_color"])
    if g.get("material"):
        parts.append(g["material"])
    if g.get("formality"):
        parts.append(g["formality"])
    bits.append(" · ".join(parts))
    if g.get("brand"):
        bits.append(f"Marca: {g['brand']}")
    if g.get("model_name"):
        bits.append(f"Modelo: {g['model_name']}")
    return "\n".join(bits)


# --------------------------------------------------------------------------- #
# Orquestrador
# --------------------------------------------------------------------------- #
def handle_update(update: dict) -> None:
    """Ponto de entrada chamado pelo webhook. Faz tudo e responde no chat."""
    settings = get_settings()
    tg = Telegram(settings.telegram_bot_token)

    # --- identifica remetente e whitelist ---
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg.get("from", {}).get("id")
    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        user_id = cq.get("from", {}).get("id")
    else:
        return

    if settings.telegram_allowed_ids and user_id not in settings.telegram_allowed_ids:
        tg.send_message(chat_id, "🚫 Desculpe, este guarda-roupa é particular.")
        return

    try:
        if "callback_query" in update:
            _handle_callback(tg, chat_id, update["callback_query"])
        elif "photo" in update.get("message", {}):
            _handle_photo(tg, chat_id, update["message"])
        elif "text" in update.get("message", {}):
            _handle_text(tg, chat_id, update["message"]["text"])
    except Exception:  # nunca deixe o webhook estourar 500 para o Telegram
        logger.exception("Erro tratando update")
        tg.send_message(chat_id, "😖 Deu um problema ao processar. Pode tentar de novo?")


def _handle_photo(tg: Telegram, chat_id: int, msg: dict) -> None:
    # maior resolução disponível é o último item de photo[]
    file_id = msg["photo"][-1]["file_id"]

    # Modo rápido: só enfileira e confirma com uma reação (o worker cataloga
    # em segundo plano). Aguenta rajada de fotos sem travar o webhook.
    if storage.get_fast_mode(chat_id):
        storage.enqueue_ingest(chat_id, file_id)
        tg.react(chat_id, msg["message_id"])
        return

    tg.send_message(chat_id, "🔍 Analisando a peça...")
    raw = tg.download_photo(file_id)

    try:
        norm = normalize_image(raw)
    except ImageValidationError:
        tg.send_message(chat_id, "🤔 Não consegui ler essa imagem. Tenta outra foto?")
        return

    if storage.find_existing_id(norm.content_hash):
        tg.send_message(chat_id, "👗 Essa peça já está no guarda-roupa!")
        return

    try:
        meta = extract_garment(norm.jpeg_bytes)
    except ExtractionError:
        tg.send_message(chat_id, "😖 A IA não respondeu agora. Tenta de novo em instantes.")
        return

    if not meta.is_garment:
        tg.send_message(chat_id, "🤔 Não reconheci uma peça de roupa nessa foto. Manda outra?")
        return

    garment_id = storage.new_garment_id()
    image_path = storage.upload_image(garment_id, norm.jpeg_bytes)
    storage.insert_garment(
        image_path=image_path,
        content_hash=norm.content_hash,
        meta=meta,
        garment_id=garment_id,
        status="processed",
    )

    # embedding p/ busca semântica — não-fatal: a peça já está salva
    try:
        g0 = storage.get_garment(garment_id)
        storage.update_embedding(garment_id, embeddings.embed(embeddings.garment_text(g0)))
    except Exception:
        logger.exception("falha ao gerar embedding de %s", garment_id)

    _ask_confirm(tg, chat_id, garment_id)


def _ask_confirm(tg: Telegram, chat_id: int, garment_id: str) -> None:
    """Mostra o resumo e os botões de confirmar / corrigir (laço de edição)."""
    _set_session(chat_id, garment_id, "await_cat")
    g = storage.get_garment(garment_id)
    tg.send_message(
        chat_id,
        f"{_summary(g)}\n\nEstá tudo certo?",
        keyboard=[
            [{"text": "✅ Está certo", "callback_data": "confirm"}],
            [{"text": "✏️ Corrigir algo", "callback_data": "edit"}],
        ],
    )


def _handle_callback(tg: Telegram, chat_id: int, cq: dict) -> None:
    data = cq.get("data", "")
    tg.answer_callback(cq["id"])
    session = _get_session(chat_id)
    if not session:
        return
    garment_id = session["garment_id"]

    if data == "confirm":
        _ask_brand(tg, chat_id, garment_id)
    elif data == "edit":
        rows = [[{"text": label, "callback_data": f"f:{field}"}] for field, label in EDIT_FIELDS]
        tg.send_message(chat_id, "O que você quer corrigir?", keyboard=rows)
    elif data.startswith("f:"):
        field = data.split(":", 1)[1]
        if field in FIELD_ENUMS:
            tg.send_message(chat_id, "Escolha o valor correto:", keyboard=_value_keyboard(field))
    elif data.startswith("v:"):
        _, field, value = data.split(":", 2)
        col, enum = FIELD_ENUMS.get(field, (None, None))
        if col and value in {e.value for e in enum}:
            storage.update_garment(garment_id, {col: value})
        _ask_confirm(tg, chat_id, garment_id)  # volta ao resumo p/ corrigir mais ou confirmar
    elif data == "skip_brand":
        _ask_model(tg, chat_id, garment_id)
    elif data == "skip_model":
        _finish(tg, chat_id, garment_id)


def _handle_text(tg: Telegram, chat_id: int, text: str) -> None:
    text = text.strip()
    if text.startswith("/start") or text.startswith("/help"):
        tg.send_message(
            chat_id,
            "📸 Me mande a *foto* de uma peça que eu cataloga no guarda-roupa "
            "e pergunto a marca e o modelo.\n\n"
            "💡 _Dica: fotografe a peça sobre uma superfície de cor *contrastante* "
            "(evite roupa branca sobre lençol branco) — fica muito melhor no acervo._\n\n"
            "⚡ `/rapido` — liga o *modo rápido*: você só manda as fotos (mesmo várias "
            "de uma vez), eu catalogo em segundo plano sem perguntar nada, e você "
            "ajusta o que quiser depois no site. Mande `/rapido` de novo para desligar.\n\n"
            "✨ Ou peça um look pronto:\n"
            "• `/look` — um look qualquer\n"
            "• `/look festa` — por ocasião (festa, trabalho, encontro, praia…)\n"
            "• `/look trabalho frio` — ocasião + clima (frio/ameno/quente) decide o casaco\n"
            "• `/look encontro inverno quente` — pode juntar estação + temperatura\n\n"
            "🔎 Busca por descrição:\n"
            "• `/buscar blusa leve pra viagem`",
        )
        return

    if text.startswith("/rapido") or text.startswith("/rápido"):
        fast = not storage.get_fast_mode(chat_id)
        storage.set_fast_mode(chat_id, fast)
        if fast:
            tg.send_message(
                chat_id,
                "⚡ *Modo rápido ligado!* Manda as fotos das peças (pode mandar várias "
                "de uma vez) que eu vou catalogando em segundo plano — confirmo cada "
                "uma com um 👍 e aviso quando o lote terminar.\n\n"
                "_Qualquer ajuste (categoria, cor, marca…) você faz direto no site._\n\n"
                "Para voltar ao modo com confirmação, mande `/rapido` de novo.",
            )
        else:
            tg.send_message(
                chat_id,
                "💬 *Modo rápido desligado.* Volto a analisar na hora e confirmar "
                "categoria + marca/modelo a cada foto.",
            )
        return

    if text.startswith("/look"):
        _handle_look(tg, chat_id, text)
        return

    if text.startswith("/buscar") or text.startswith("/busca"):
        _handle_search(tg, chat_id, text)
        return

    session = _get_session(chat_id)
    if not session:
        tg.send_message(
            chat_id,
            "📸 Manda uma foto de uma peça para começar!\n"
            "💡 _De preferência sobre um fundo de cor contrastante._",
        )
        return

    garment_id = session["garment_id"]
    if session["step"] == "await_brand":
        storage.update_garment(garment_id, {"brand": text})
        _ask_model(tg, chat_id, garment_id)
    elif session["step"] == "await_model":
        storage.update_garment(garment_id, {"model_name": text})
        _finish(tg, chat_id, garment_id)


def _ask_brand(tg: Telegram, chat_id: int, garment_id: str) -> None:
    _set_session(chat_id, garment_id, "await_brand")
    tg.send_message(
        chat_id,
        "🏷️ Qual é a *marca*? (digite ou toque em Pular)",
        keyboard=[[{"text": "Pular", "callback_data": "skip_brand"}]],
    )


def _ask_model(tg: Telegram, chat_id: int, garment_id: str) -> None:
    _set_session(chat_id, garment_id, "await_model")
    tg.send_message(
        chat_id,
        "🔖 E o *modelo/coleção*? (digite ou toque em Pular)",
        keyboard=[[{"text": "Pular", "callback_data": "skip_model"}]],
    )


def _finish(tg: Telegram, chat_id: int, garment_id: str) -> None:
    _clear_session(chat_id)
    g = storage.get_garment(garment_id)
    tg.send_message(chat_id, f"✅ Salvo no guarda-roupa!\n\n{_summary(g)}")


# --------------------------------------------------------------------------- #
# Composição de looks
# --------------------------------------------------------------------------- #
# Nomes amigáveis dos slots essenciais que podem faltar para completar o look.
MISSING_LABELS = {
    "top": "uma blusa/top",
    "bottom": "uma calça ou saia",
    "footwear": "um calçado",
    "full_body": "um vestido/macacão",
}


def _piece_line(g: dict) -> str:
    label = CATEGORY_LABELS.get(g["category"], g["category"])
    name = (g.get("subcategory") or g["category"]).replace("_", " ")
    extra = " · ".join(p for p in (g.get("primary_color"), g.get("brand")) if p)
    return f"{label} {name}" + (f" ({extra})" if extra else "")


def _look_caption(occasion, season, pieces: list[dict], rationale: str | None) -> str:
    titulo = f"Look {occasion.replace('_', ' ')}" if occasion else "Seu look"
    head = f"✨ *{titulo}*" + (f" · {season}" if season else "")
    lines = [head, ""] + [f"• {_piece_line(g)}" for g in pieces]
    if rationale:
        lines += ["", f"_{rationale}_"]
    return "\n".join(lines)


def _styled_look(
    garments, occasion, season, temperature=None, boldness=None
) -> tuple[list[dict], str | None]:
    """Look pré-computado (curadoria do Claude) quando existe; senão motor de regras.
    Sem IA em tempo real."""
    by_id = {g["id"]: g for g in garments}
    curated = storage.get_curated_looks(occasion, season, temperature, boldness)
    if not curated and boldness:
        curated = storage.get_curated_looks(occasion, season, temperature, None)
    if curated:
        row = random.choice(curated)
        chosen = [by_id[i] for i in (row.get("garment_ids") or []) if i in by_id]
        if chosen:
            return chosen, row.get("rationale")
    return looks.compose(
        garments, occasion=occasion, season=season, temperature=temperature
    ).pieces, None


def _handle_look(tg: Telegram, chat_id: int, text: str) -> None:
    args = text[len("/look"):]
    occasion = looks.parse_occasion(args)
    season = looks.parse_season(args)
    temperature = looks.parse_temperature(args)
    boldness = looks.parse_boldness(args)

    garments = storage.fetch_garments()
    pieces, rationale = _styled_look(garments, occasion, season, temperature, boldness)

    if not pieces:
        tg.send_message(
            chat_id,
            "🤔 Ainda não tenho peças suficientes pra montar um look. "
            "Cadastre mais peças mandando fotos!",
        )
        return

    caption = _look_caption(occasion, season, pieces, rationale)
    urls = [u for g in pieces if (u := storage.signed_url(g["image_path"]))]
    if len(urls) >= 2:
        tg.send_media_group(chat_id, urls, caption)
    elif len(urls) == 1:
        tg.send_photo(chat_id, urls[0], caption)
    else:
        tg.send_message(chat_id, caption)

    missing = looks.missing_slots(pieces)
    if missing:
        faltam = ", ".join(MISSING_LABELS.get(m, m) for m in missing)
        tg.send_message(
            chat_id,
            f"⚠️ Faltou {faltam} pra completar o look. Cadastre essas peças e o look fica completo!",
        )

    if looks.cold_without_coat(pieces, temperature):
        tg.send_message(
            chat_id,
            "🧥 Está frio e eu não achei um casaco elegível no acervo — vale cadastrar um agasalho.",
        )


def _handle_search(tg: Telegram, chat_id: int, text: str) -> None:
    parts = text.split(maxsplit=1)
    query = parts[1].strip() if len(parts) > 1 else ""
    if not query:
        tg.send_message(chat_id, "🔎 Use assim: `/buscar blusa leve pra viagem`")
        return

    try:
        vec = embeddings.embed(query, embeddings.TASK_QUERY)
    except Exception:
        logger.exception("falha ao embeddar a consulta")
        tg.send_message(chat_id, "😖 Não consegui buscar agora. Tenta de novo em instantes.")
        return

    matches = storage.match_garments(vec, match_count=5)
    if not matches:
        tg.send_message(chat_id, "🤔 Não achei nada parecido no guarda-roupa.")
        return

    caption = f"🔎 *Resultados para:* {query}\n\n" + "\n".join(
        f"• {_piece_line(m)} _({round(m.get('similarity', 0) * 100)}%)_" for m in matches
    )
    urls = [u for m in matches if (u := storage.signed_url(m["image_path"]))]
    if len(urls) >= 2:
        tg.send_media_group(chat_id, urls, caption)
    elif len(urls) == 1:
        tg.send_photo(chat_id, urls[0], caption)
    else:
        tg.send_message(chat_id, caption)
