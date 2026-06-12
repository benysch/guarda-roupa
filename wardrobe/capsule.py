"""
Engine de mala de viagem (cápsula).

O problema é o inverso da gap analysis: em vez de "que peça adicionada maximiza
os looks possíveis?", aqui é "qual o MENOR subconjunto do acervo que cobre todos
os looks da viagem?". Cobertura gulosa sobre o mesmo motor de regras de looks.py
(slots do corpo, formalidade, estação, harmonia de cor, paleta).

É LÓGICA PURA — não faz IO nem conhece Telegram/clima. A camada de cima traduz
a viagem em TripSlots (1 slot = 1 look necessário: "seg — trabalho", "seg —
jantar") com a estação/clima de cada dia, e apresenta o resultado.

Heurística de empacotamento, na ordem:
  1. camada visível (top/full_body) RODA entre dias consecutivos — ninguém quer
     repetir a mesma blusa dois dias seguidos, mesmo que caiba na mala;
  2. fora isso, peça JÁ NA MALA vence peça nova (mala mínima);
  3. neutro da paleta > statement favorável > cor 'evita' (demoção, não bloqueio);
  4. desempate por utilidade futura (em quantos slots restantes a peça serve)
     e por id (determinismo — sem random, rerun = mesma mala).

Bottoms, calçados e casacos repetem livremente: é assim que cápsulas funcionam
(rodar a camada de cima sobre poucas bases).
"""

from dataclasses import dataclass, field
from typing import Optional

from . import looks
from .schema import Category, Season


# Estações em que o look pede casaco.
_COLD = {Season.OUTONO.value, Season.INVERNO.value}

_CATEGORY_ORDER = [
    Category.FULL_BODY.value,
    Category.TOP.value,
    Category.BOTTOM.value,
    Category.OUTERWEAR.value,
    Category.FOOTWEAR.value,
    Category.BAG.value,
    Category.ACCESSORY.value,
]


@dataclass(frozen=True)
class TripSlot:
    """Um look necessário na viagem (ex.: 'ter 22/09 — jantar')."""

    label: str
    occasion: Optional[str] = None
    season: Optional[str] = None


@dataclass
class SlotLook:
    slot: TripSlot
    pieces: list[dict] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


@dataclass
class Capsule:
    pieces: list[dict]
    looks: list[SlotLook]

    @property
    def uncovered(self) -> list[SlotLook]:
        """Slots que o acervo não cobriu por completo (entrada da gap analysis)."""
        return [sl for sl in self.looks if sl.missing]

    def by_category(self) -> dict[str, list[dict]]:
        """Lista de mala agrupada por categoria, em ordem de empacotamento."""
        out: dict[str, list[dict]] = {}
        for cat in _CATEGORY_ORDER:
            grp = [g for g in self.pieces if g.get("category") == cat]
            if grp:
                out[cat] = grp
        return out


def _excluded(occasion: Optional[str]) -> set[str]:
    excluded = set(looks._EXCLUDED_DEFAULT)
    if occasion == looks.Occasion.PRAIA.value:
        excluded.discard(Category.BEACHWEAR.value)
    if occasion == looks.Occasion.CASA.value:
        excluded.discard(Category.SLEEPWEAR.value)
    return excluded


def _target_rank(occasion: Optional[str]) -> Optional[int]:
    if occasion and occasion in looks._OCCASION_FORMALITY:
        return looks.FORMALITY_RANK[looks._OCCASION_FORMALITY[occasion]]
    return None


def _slot_cands(
    pool: list[dict], category: str, target_rank, season, colors: list[str]
) -> list[dict]:
    return [
        g
        for g in pool
        if g.get("category") == category
        and looks._formality_ok(target_rank, g)
        and looks._season_ok(g, season)
        and looks._color_ok(colors, g.get("primary_color"))
    ]


def _eligibility(garments: list[dict], slots: list[TripSlot]) -> dict[str, int]:
    """Em quantos slots da viagem cada peça serve (utilidade futura p/ desempate)."""
    count: dict[str, int] = {}
    for slot in slots:
        rank = _target_rank(slot.occasion)
        for g in garments:
            if looks._formality_ok(rank, g) and looks._season_ok(g, slot.season):
                count[g["id"]] = count.get(g["id"], 0) + 1
    return count


def _pick(
    cands: list[dict],
    packed: set[str],
    elig: dict[str, int],
    prev_visible: Optional[str] = None,
    visible: bool = False,
) -> Optional[dict]:
    """Melhor candidato segundo a heurística de empacotamento (determinístico)."""
    if not cands:
        return None

    def key(g: dict):
        rot = 1 if visible and g.get("id") == prev_visible else 0
        new = 0 if g.get("id") in packed else 1
        c = g.get("primary_color")
        color = 0 if c in looks.NEUTRALS else (2 if c in looks.AVOID else 1)
        return (rot, new, color, -elig.get(g.get("id"), 0), str(g.get("id")))

    return min(cands, key=key)


def pack(
    garments: list[dict], slots: list[TripSlot], include_bag: bool = True
) -> Capsule:
    """Monta a mala mínima que cobre os slots da viagem.

    Devolve a cápsula com a lista de peças, o look de cada slot e os slots
    descobertos (com os papéis faltantes) — insumo direto para a gap analysis.
    """
    elig = _eligibility(garments, slots)
    packed: set[str] = set()
    pieces: list[dict] = []
    slot_looks: list[SlotLook] = []
    prev_visible: Optional[str] = None

    def commit(g: dict, look: list[dict], colors: list[str]) -> None:
        look.append(g)
        colors.append(g.get("primary_color"))
        if g["id"] not in packed:
            packed.add(g["id"])
            pieces.append(g)

    for slot in slots:
        rank = _target_rank(slot.occasion)
        excl = _excluded(slot.occasion)
        pool = [g for g in garments if g.get("category") not in excl]

        look: list[dict] = []
        colors: list[str] = []

        # --- base: full_body OU top+bottom — a opção que adiciona menos peças
        # novas à mala vence; empate prefere top+bottom (recombina melhor).
        full = _pick(
            _slot_cands(pool, Category.FULL_BODY.value, rank, slot.season, colors),
            packed, elig, prev_visible, visible=True,
        )
        top = _pick(
            _slot_cands(pool, Category.TOP.value, rank, slot.season, colors),
            packed, elig, prev_visible, visible=True,
        )
        bottom = None
        if top is not None:
            bottom = _pick(
                _slot_cands(
                    pool, Category.BOTTOM.value, rank, slot.season,
                    [top.get("primary_color")],
                ),
                packed, elig,
            )

        def novas(*gs) -> int:
            return sum(1 for g in gs if g is not None and g["id"] not in packed)

        if full is not None and (
            not (top and bottom) or novas(full) < novas(top, bottom)
        ):
            commit(full, look, colors)
            prev_visible = full["id"]
        elif top is not None:
            commit(top, look, colors)
            prev_visible = top["id"]
            if bottom is not None:
                commit(bottom, look, colors)

        # --- calçado (essencial) ---
        shoe = _pick(
            _slot_cands(pool, Category.FOOTWEAR.value, rank, slot.season, colors),
            packed, elig,
        )
        if shoe is not None:
            commit(shoe, look, colors)

        # --- casaco quando o clima do dia pede ---
        if slot.season in _COLD:
            outer = _pick(
                _slot_cands(pool, Category.OUTERWEAR.value, rank, slot.season, colors),
                packed, elig,
            )
            if outer is not None:
                commit(outer, look, colors)

        slot_looks.append(
            SlotLook(slot=slot, pieces=look, missing=looks.missing_slots(look))
        )

    # --- bolsa: no máximo UMA para a viagem inteira, neutra de preferência ---
    if include_bag:
        bags = [g for g in garments if g.get("category") == Category.BAG.value]
        bag = _pick(bags, packed, elig)
        if bag is not None and bag["id"] not in packed:
            packed.add(bag["id"])
            pieces.append(bag)

    return Capsule(pieces=pieces, looks=slot_looks)
