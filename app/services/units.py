"""Kleine, sichere Einheiten-Normalisierung für Mengen im Einkaufszettel."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BaseAmount:
    amount: float
    unit: str
    dimension: str


_ALIASES = {
    "g": "g", "gr": "g", "gramm": "g",
    "kg": "kg", "kilogramm": "kg",
    "ml": "ml", "milliliter": "ml",
    "l": "l", "liter": "l",
    "stk": "Stück", "st": "Stück", "stück": "Stück", "stueck": "Stück",
    "dose": "Dose", "dosen": "Dose", "glas": "Glas", "gläser": "Glas", "glaeser": "Glas",
    "packung": "Packung", "pkg": "Packung", "päckchen": "Packung", "paeckchen": "Packung",
    "bund": "Bund", "becher": "Becher", "flasche": "Flasche",
    "el": "EL", "esslöffel": "EL", "essloeffel": "EL",
    "tl": "TL", "teelöffel": "TL", "teeloeffel": "TL",
}


def normalize_unit(unit: Optional[str]) -> str:
    raw = (unit or "").strip()
    return _ALIASES.get(raw.casefold().rstrip("."), raw)


def to_base(amount: float, unit: Optional[str]) -> Optional[BaseAmount]:
    normalized = normalize_unit(unit)
    if normalized == "g": return BaseAmount(amount, "g", "mass")
    if normalized == "kg": return BaseAmount(amount * 1000, "g", "mass")
    if normalized == "ml": return BaseAmount(amount, "ml", "volume")
    if normalized == "l": return BaseAmount(amount * 1000, "ml", "volume")
    if normalized in {"Stück", "Dose", "Glas", "Packung", "Bund", "Becher", "Flasche", "EL", "TL"}:
        return BaseAmount(amount, normalized, f"count:{normalized}")
    if not normalized:
        return BaseAmount(amount, "", "count:plain")
    return None


def pretty_base(amount: float, dimension: str) -> tuple[float, str]:
    if dimension == "mass" and amount >= 1000:
        return round(amount / 1000, 3), "kg"
    if dimension == "volume" and amount >= 1000:
        return round(amount / 1000, 3), "l"
    if dimension == "mass": return round(amount, 3), "g"
    if dimension == "volume": return round(amount, 3), "ml"
    return round(amount, 3), dimension.removeprefix("count:")
