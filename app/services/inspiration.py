"""Kleine kuratierte Rezept-Inspiration über dieselbe Chefkoch-Suche."""
from datetime import date
from app.services import chefkoch

_CATEGORIES = [
    ("schnell", "⏱ Schnell", "schnelle Küche"),
    ("vegetarisch", "🥦 Vegetarisch", "vegetarisch"),
    ("klassiker", "🍲 Klassiker", "Klassiker"),
    ("pasta", "🍝 Pasta", "Pasta"),
    ("ofen", "🔥 Ofengerichte", "Ofengericht"),
    ("salat", "🥗 Salate", "Salat"),
]


def categories() -> list[dict]:
    month = date.today().month
    seasonal = ("saisonal", "🍂 Saisonal", "Kürbis Herbstküche") if month in {9, 10, 11} else ("saisonal", "🌿 Saisonal", "Saisonküche")
    return [{"slug": s, "label": l, "query": q} for s, l, q in [seasonal, *_CATEGORIES]]


def results_for(slug: str, limit: int = 12):
    row = next((c for c in categories() if c["slug"] == slug), None)
    if row is None:
        return None
    return chefkoch.cached_search(row["query"], limit)
