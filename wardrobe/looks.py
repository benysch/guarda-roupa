"""
Engine de composição de looks.

Recebe o acervo (lista de dicts vindos do Postgres) e monta um look coerente:
um item por slot do corpo, respeitando formalidade, estação, ocasião e harmonia
de cor. É LÓGICA PURA — não faz IO nem conhece Telegram/Supabase — para ser
reaproveitada pelo app futuro. A camada de bot só fornece os dados e apresenta.

Regra de slots:
  look = (full_body)  OU  (top + bottom)   + footwear
         + opcionalmente outerwear / bag / 1 accessory
Exclui por padrão lingerie/sleepwear/beachwear (beachwear volta se ocasião=praia,
sleepwear se ocasião=casa).
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from .schema import Category, ColorFamily, Formality, Occasion, Season

# Escala ordenada de formalidade -> permite medir "distância" entre peças.
_FORMALITY_ORDER = [
    Formality.CASUAL,
    Formality.SMART_CASUAL,
    Formality.TRABALHO,
    Formality.COCKTAIL,
    Formality.GALA,
]
FORMALITY_RANK = {f.value: i for i, f in enumerate(_FORMALITY_ORDER)}

# Neutros combinam com tudo; o resto é cor "statement" (no máx. uma por look).
NEUTRALS = {
    ColorFamily.PRETO.value,
    ColorFamily.BRANCO.value,
    ColorFamily.CINZA.value,
    ColorFamily.BEGE.value,
    ColorFamily.MARROM.value,
    ColorFamily.DOURADO.value,
    ColorFamily.PRATEADO.value,
    ColorFamily.MULTICOR.value,
}

# Categorias que não entram num look "de rua" comum.
_EXCLUDED_DEFAULT = {
    Category.LINGERIE.value,
    Category.SLEEPWEAR.value,
    Category.BEACHWEAR.value,
}

# Formalidade-alvo sugerida por ocasião (usada quando o usuário pede /look <ocasião>).
_OCCASION_FORMALITY = {
    Occasion.DIA_A_DIA.value: Formality.CASUAL.value,
    Occasion.CASA.value: Formality.CASUAL.value,
    Occasion.ACADEMIA.value: Formality.CASUAL.value,
    Occasion.PRAIA.value: Formality.CASUAL.value,
    Occasion.VIAGEM.value: Formality.CASUAL.value,
    Occasion.ENCONTRO.value: Formality.SMART_CASUAL.value,
    Occasion.TRABALHO.value: Formality.TRABALHO.value,
    Occasion.FESTA.value: Formality.COCKTAIL.value,
    Occasion.CASAMENTO.value: Formality.GALA.value,
}

# Apelidos em pt-BR (texto livre do comando) -> valor do Enum.
_OCCASION_ALIASES = {
    "dia": Occasion.DIA_A_DIA.value,
    "diaadia": Occasion.DIA_A_DIA.value,
    "dia_a_dia": Occasion.DIA_A_DIA.value,
    "trabalho": Occasion.TRABALHO.value,
    "work": Occasion.TRABALHO.value,
    "festa": Occasion.FESTA.value,
    "balada": Occasion.FESTA.value,
    "casamento": Occasion.CASAMENTO.value,
    "praia": Occasion.PRAIA.value,
    "academia": Occasion.ACADEMIA.value,
    "treino": Occasion.ACADEMIA.value,
    "viagem": Occasion.VIAGEM.value,
    "encontro": Occasion.ENCONTRO.value,
    "date": Occasion.ENCONTRO.value,
    "casa": Occasion.CASA.value,
}
_SEASON_ALIASES = {
    "verao": Season.VERAO.value,
    "verão": Season.VERAO.value,
    "inverno": Season.INVERNO.value,
    "outono": Season.OUTONO.value,
    "primavera": Season.PRIMAVERA.value,
}


@dataclass
class Look:
    """Resultado da composição: peças escolhidas + slots essenciais que faltaram."""

    pieces: list[dict] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)  # categorias essenciais ausentes
    occasion: Optional[str] = None
    season: Optional[str] = None

    @property
    def complete(self) -> bool:
        return not self.missing


def parse_occasion(text: str) -> Optional[str]:
    for token in text.lower().split():
        if token in _OCCASION_ALIASES:
            return _OCCASION_ALIASES[token]
    return None


def parse_season(text: str) -> Optional[str]:
    for token in text.lower().split():
        if token in _SEASON_ALIASES:
            return _SEASON_ALIASES[token]
    return None


# --------------------------------------------------------------------------- #
# Filtros de coerência
# --------------------------------------------------------------------------- #
def _formality_ok(target_rank: Optional[int], g: dict, tol: int = 1) -> bool:
    if target_rank is None:
        return True
    r = FORMALITY_RANK.get(g.get("formality"))
    return r is not None and abs(r - target_rank) <= tol


def _season_ok(g: dict, season: Optional[str]) -> bool:
    if not season:
        return True
    seasons = g.get("seasons") or []
    return not seasons or season in seasons  # vazio = peça atemporal


def _color_ok(colors: list[str], candidate: str) -> bool:
    if candidate in NEUTRALS:
        return True
    statements = [c for c in colors if c not in NEUTRALS]
    return all(c == candidate for c in statements)  # no máx. uma cor statement


def _cands(pools: list[list[dict]], category: str, target_rank, season, colors) -> list[dict]:
    """Candidatos do slot, tentando cada pool em ordem (preferida -> ampla)."""
    for pool in pools:
        hits = [
            g
            for g in pool
            if g.get("category") == category
            and _formality_ok(target_rank, g)
            and _season_ok(g, season)
            and _color_ok(colors, g.get("primary_color"))
        ]
        if hits:
            return hits
    return []


def missing_slots(pieces: list[dict]) -> list[str]:
    """Slots essenciais ausentes num conjunto de peças (top+bottom ou full_body, + footwear)."""
    present = {g.get("category") for g in pieces}
    missing: list[str] = []
    if Category.FULL_BODY.value not in present:
        if Category.TOP.value not in present:
            missing.append(Category.TOP.value)
        if Category.BOTTOM.value not in present:
            missing.append(Category.BOTTOM.value)
    if Category.FOOTWEAR.value not in present:
        missing.append(Category.FOOTWEAR.value)
    return missing


def candidates(
    garments: list[dict], occasion: Optional[str] = None, limit: int = 60
) -> list[dict]:
    """Acervo elegível para o estilista IA: remove categorias incompatíveis com um
    look de rua e prioriza as peças da ocasião. Coerência de cor/taste fica com o
    estilista — aqui só garantimos que as peças existem e fazem sentido no slot."""
    excluded = set(_EXCLUDED_DEFAULT)
    if occasion == Occasion.PRAIA.value:
        excluded.discard(Category.BEACHWEAR.value)
    if occasion == Occasion.CASA.value:
        excluded.discard(Category.SLEEPWEAR.value)
    pool = [g for g in garments if g.get("category") not in excluded]
    if occasion:
        pool.sort(key=lambda g: 0 if occasion in (g.get("occasions") or []) else 1)
    return pool[:limit]


# --------------------------------------------------------------------------- #
# Composição (motor de regras — usado como fallback do estilista IA)
# --------------------------------------------------------------------------- #
def compose(
    garments: list[dict],
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> Look:
    rng = rng or random

    excluded = set(_EXCLUDED_DEFAULT)
    if occasion == Occasion.PRAIA.value:
        excluded.discard(Category.BEACHWEAR.value)
    if occasion == Occasion.CASA.value:
        excluded.discard(Category.SLEEPWEAR.value)

    pool_all = [g for g in garments if g.get("category") not in excluded]
    if occasion:
        pool_pref = [g for g in pool_all if occasion in (g.get("occasions") or [])]
        pools = [pool_pref, pool_all]
    else:
        pools = [pool_all]

    target_rank: Optional[int] = None
    if occasion and occasion in _OCCASION_FORMALITY:
        target_rank = FORMALITY_RANK[_OCCASION_FORMALITY[occasion]]

    chosen: list[dict] = []
    colors: list[str] = []

    def commit(g: dict) -> None:
        chosen.append(g)
        colors.append(g.get("primary_color"))

    # --- base: full_body OU top+bottom ---
    full_cands = _cands(pools, Category.FULL_BODY.value, target_rank, season, colors)
    top_cands = _cands(pools, Category.TOP.value, target_rank, season, colors)
    bottom_cands = _cands(pools, Category.BOTTOM.value, target_rank, season, colors)

    prefer_full = bool(full_cands) and (not (top_cands and bottom_cands) or rng.random() < 0.4)
    if prefer_full:
        commit(rng.choice(full_cands))
    else:
        if top_cands:
            commit(rng.choice(top_cands))
        # o bottom precisa harmonizar com a cor já escolhida
        bottom_cands = _cands(pools, Category.BOTTOM.value, target_rank, season, colors)
        if bottom_cands:
            commit(rng.choice(bottom_cands))

    # se não havia ocasião, fixa a formalidade-alvo pela peça-base escolhida
    if target_rank is None and chosen:
        target_rank = FORMALITY_RANK.get(chosen[0].get("formality"))

    # --- calçado (essencial) ---
    shoe_cands = _cands(pools, Category.FOOTWEAR.value, target_rank, season, colors)
    if shoe_cands:
        commit(rng.choice(shoe_cands))

    # --- extras opcionais ---
    if season in (Season.OUTONO.value, Season.INVERNO.value) or rng.random() < 0.25:
        outer = _cands(pools, Category.OUTERWEAR.value, target_rank, season, colors)
        if outer:
            commit(rng.choice(outer))

    if rng.random() < 0.6:
        bag = _cands(pools, Category.BAG.value, target_rank, season, colors)
        if bag:
            commit(rng.choice(bag))

    if rng.random() < 0.5:
        acc = _cands(pools, Category.ACCESSORY.value, target_rank, season, colors)
        if acc:
            commit(rng.choice(acc))

    return Look(
        pieces=chosen,
        missing=missing_slots(chosen),
        occasion=occasion,
        season=season,
    )
