"""Chefkoch-Anbindung über die undokumentierte v2-API (Phase 2).

Defensiv laut Plan: echter User-Agent, lokal cachen, drosseln, robuste Fehler.
Rezeptdetails werden dauerhaft als JSON-Datei gecacht (ändern sich praktisch nie),
Suchanfragen gehen live raus (mit kleiner Mindestpause zwischen Requests).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

from app.config import BASE_DIR

API_BASE = "https://api.chefkoch.de/v2"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
CACHE_DIR = BASE_DIR / "data" / "cache" / "chefkoch"
SEARCH_CACHE_DIR = BASE_DIR / "data" / "cache" / "chefkoch_search"
SEARCH_CACHE_TTL = 24 * 3600  # Sekunden
MIN_REQUEST_INTERVAL = 1.0  # Sekunden Mindestabstand zwischen Live-Requests
REQUEST_TIMEOUT = 20.0

_last_request_ts = 0.0


class ChefkochError(RuntimeError):
    """Fehler beim Zugriff auf die Chefkoch-API."""


@dataclass
class SearchResult:
    chefkoch_id: str
    title: str
    subtitle: str
    image_url: Optional[str]
    rating: Optional[float]
    num_votes: int
    site_url: str
    # Zusätzlich in der Suchantwort enthalten (kein Extra-Request nötig) —
    # macht Such-/Inspirationskarten aussagekräftiger.
    difficulty: Optional[int] = None
    preparation_time: Optional[int] = None
    kcalories: Optional[int] = None


def _throttle() -> None:
    """Sorgt für einen Mindestabstand zwischen Live-Requests (Höflichkeit)."""
    global _last_request_ts
    elapsed = time.monotonic() - _last_request_ts
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_ts = time.monotonic()


def _get(url: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    _throttle()
    try:
        resp = httpx.get(
            url,
            params=params,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise ChefkochError(f"Chefkoch-Anfrage fehlgeschlagen: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ChefkochError("Chefkoch-Antwort war kein gültiges JSON.") from exc


def build_image_url(template: Optional[str], fmt: str = "crop-360x240") -> Optional[str]:
    """Ersetzt den `<format>`-Platzhalter in Chefkochs Bild-URL-Template."""
    if not template:
        return None
    return template.replace("<format>", fmt)


_ID_RE = re.compile(r"(\d{6,})")


def extract_recipe_id(text: str) -> Optional[str]:
    text = (text or "").strip()
    if not text:
        return None
    if text.isdigit():
        return text
    m = re.search(r"/rezepte/(\d+)", text)
    if m:
        return m.group(1)
    m = _ID_RE.search(text)
    return m.group(1) if m else None


def search(query: str, limit: int = 12, offset: int = 0) -> list[SearchResult]:
    query = (query or "").strip()
    if not query:
        return []
    data = _get(f"{API_BASE}/recipes", params={"query": query, "limit": limit, "offset": offset})
    results: list[SearchResult] = []
    for entry in data.get("results", []):
        r = entry.get("recipe") or {}
        rating = r.get("rating") or {}
        nutrition = r.get("nutrition") or {}
        results.append(SearchResult(chefkoch_id=str(r.get("id", "")), title=r.get("title", "(ohne Titel)"), subtitle=r.get("subtitle") or "", image_url=build_image_url(r.get("previewImageUrlTemplate")), rating=rating.get("rating"), num_votes=rating.get("numVotes", 0), site_url=r.get("siteUrl", ""), difficulty=r.get("difficulty"), preparation_time=r.get("preparationTime"), kcalories=nutrition.get("kCalories")))
    return results


def _search_cache_path(term: str) -> Path:
    slug = re.sub(r"[^a-z0-9äöüß]+", "-", term.lower()).strip("-") or "leer"
    return SEARCH_CACHE_DIR / f"{slug}.json"


def cached_search(term: str, limit: int = 12, ttl: float = SEARCH_CACHE_TTL) -> list[SearchResult]:
    path = _search_cache_path(term)
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - payload.get("ts", 0) < ttl:
                return [SearchResult(**e) for e in payload["results"][:limit]]
        except (OSError, json.JSONDecodeError, TypeError, KeyError):
            pass
    results = search(term, limit=limit)
    try:
        SEARCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"ts": time.time(), "results": [vars(r) for r in results]}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return results


def _cache_path(chefkoch_id: str) -> Path:
    return CACHE_DIR / f"{chefkoch_id}.json"


def fetch_recipe(chefkoch_id: str, *, use_cache: bool = True) -> dict[str, Any]:
    chefkoch_id = str(chefkoch_id).strip()
    if not chefkoch_id.isdigit():
        raise ChefkochError(f"Ungültige Rezept-ID: {chefkoch_id!r}")
    path = _cache_path(chefkoch_id)
    if use_cache and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    data = _get(f"{API_BASE}/recipes/{chefkoch_id}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return data


@dataclass
class ParsedIngredient:
    group_header: Optional[str]
    name: str
    amount: Optional[float]
    unit: Optional[str]
    usage_info: Optional[str]
    is_basic: bool
    source_raw_line: Optional[str] = None
    source_amount_raw: Optional[str] = None
    parse_status: str = "parsed"
    parse_error: Optional[str] = None


@dataclass
class ParsedRecipe:
    chefkoch_id: str
    title: str
    subtitle: Optional[str]
    base_servings: int
    image_url: Optional[str]
    site_url: str
    instructions: Optional[str]
    kcalories: Optional[int]
    total_time: Optional[int]
    ingredients: list[ParsedIngredient]
    raw: dict[str, Any]
    ck_rating: Optional[float] = None
    ck_num_votes: int = 0
    difficulty: Optional[int] = None
    preparation_time: Optional[int] = None
    cooking_time: Optional[int] = None
    resting_time: Optional[int] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbs_g: Optional[float] = None
    cuisine: Optional[str] = None
    has_video: bool = False
    is_premium: bool = False
    tips_html: Optional[str] = None
    tip_decisive: Optional[str] = None
    tip_common_errors: Optional[str] = None
    tip_appearance: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    meal_type: Optional[str] = None


MEAL_TYPES: list[tuple[str, str]] = [("fruehstueck", "🍳 Frühstück"), ("suppe", "🍲 Suppe"), ("salat", "🥗 Salat"), ("vorspeise", "🥟 Vorspeise"), ("beilage", "🍟 Beilage"), ("dessert", "🍰 Dessert"), ("hauptgericht", "🍽️ Hauptgericht"), ("snack", "🥨 Snack")]
_MEAL_TYPE_LABELS = dict(MEAL_TYPES)
_MEAL_TYPE_TAG_MAP = {"frühstück": "fruehstueck", "suppe": "suppe", "eintopf": "suppe", "salat": "salat", "vorspeise": "vorspeise", "beilage": "beilage", "dessert": "dessert", "süßspeise": "dessert", "süssspeise": "dessert", "hauptspeise": "hauptgericht", "snack": "snack"}


def meal_type_label(slug: Optional[str]) -> Optional[str]:
    return _MEAL_TYPE_LABELS.get(slug or "")


DIFFICULTY_LABELS = {1: "Einfach", 2: "Mittel", 3: "Anspruchsvoll"}


def difficulty_label(value: Optional[int]) -> Optional[str]:
    return DIFFICULTY_LABELS.get(value or 0)


def classify_meal_type(tags: list[str]) -> Optional[str]:
    lower_tags = {t.strip().lower() for t in tags if t and t.strip()}
    matched = {_MEAL_TYPE_TAG_MAP[t] for t in lower_tags if t in _MEAL_TYPE_TAG_MAP}
    for slug, _label in MEAL_TYPES:
        if slug in matched:
            return slug
    return None


def _clean_header(header: Optional[str]) -> Optional[str]:
    if not header:
        return None
    header = header.strip()
    return header or None


def parse_recipe(data: dict[str, Any]) -> ParsedRecipe:
    ingredients: list[ParsedIngredient] = []
    for group in data.get("ingredientGroups") or []:
        header = _clean_header(group.get("header"))
        for ing in group.get("ingredients") or []:
            name = (ing.get("name") or "").strip()
            if not name:
                continue
            raw_amount = ing.get("amount")
            parse_error = None
            if raw_amount in (None, ""):
                amount, parse_status = None, "source-missing"
            else:
                try:
                    amount, parse_status = float(raw_amount), "parsed"
                except (TypeError, ValueError):
                    amount, parse_status, parse_error = None, "parse-error", f"Ungültige Mengenangabe: {raw_amount!r}"
            unit = (ing.get("unit") or "").strip() or None
            usage_info = (ing.get("usageInfo") or "").strip() or None
            raw_line = " ".join(str(part).strip() for part in (raw_amount, unit, name, usage_info) if part not in (None, ""))
            ingredients.append(ParsedIngredient(group_header=header, name=name, amount=amount, unit=unit, usage_info=usage_info, is_basic=bool(ing.get("isBasic")), source_raw_line=raw_line, source_amount_raw=str(raw_amount) if raw_amount not in (None, "") else None, parse_status=parse_status, parse_error=parse_error))
    servings = data.get("servings")
    try:
        base_servings = max(1, int(servings))
    except (TypeError, ValueError):
        base_servings = 1
    rating, nutrition = data.get("rating") or {}, data.get("nutrition") or {}
    tags = [t.strip() for t in (data.get("tags") or []) if t and t.strip()]
    def _text(value: Optional[str]) -> Optional[str]:
        value = (value or "").strip()
        return value or None
    return ParsedRecipe(chefkoch_id=str(data.get("id", "")), title=data.get("title", "(ohne Titel)"), subtitle=(data.get("subtitle") or "").strip() or None, base_servings=base_servings, image_url=build_image_url(data.get("previewImageUrlTemplate"), "crop-960x640"), site_url=data.get("siteUrl", ""), instructions=(data.get("instructions") or "").strip() or None, kcalories=data.get("kCalories"), total_time=data.get("totalTime"), ingredients=ingredients, raw=data, ck_rating=rating.get("rating"), ck_num_votes=rating.get("numVotes") or 0, difficulty=data.get("difficulty"), preparation_time=data.get("preparationTime"), cooking_time=data.get("cookingTime"), resting_time=data.get("restingTime"), protein_g=nutrition.get("proteinContent"), fat_g=nutrition.get("fatContent"), carbs_g=nutrition.get("carbohydrateContent"), cuisine=_text(data.get("recipeCuisine")), has_video=bool(data.get("hasVideo")), is_premium=bool(data.get("isPremium")), tips_html=_text(data.get("editorialTips")), tip_decisive=_text(data.get("ckCheckDecisiveTip")), tip_common_errors=_text(data.get("ckCheckCommonErrors")), tip_appearance=_text(data.get("ckCheckAppearance")), tags=tags, meal_type=classify_meal_type(tags))
