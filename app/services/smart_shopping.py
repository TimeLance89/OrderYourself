"""Gemeinsamer intelligenter Einkaufszettel.

- dedupliziert Artikel quellenübergreifend
- addiert kompatible Mengen
- hält Rezept- und Personenherkunft fest
- sortiert in einen plausiblen Ladenlaufweg
- lernt manuelle Bereichskorrekturen dauerhaft
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Iterable
from sqlmodel import Session, select

from app.models import GroceryItem, GroceryItemRule, GroceryList, HouseholdMember, Recipe
from app.models.shopping import ITEM_BOUGHT, ITEM_OPEN, LIST_OPEN, SOURCE_RECIPE
from app.services import units

SECTION_ORDER = (
    ("Obst & Gemüse", "🥬"),
    ("Backwaren", "🥖"),
    ("Fleisch & Fisch", "🥩"),
    ("Kühlregal", "🧀"),
    ("Trockenwaren", "🥫"),
    ("Getränke", "🥤"),
    ("Tiefkühl", "❄️"),
    ("Haushalt & Drogerie", "🧴"),
    ("Sonstiges", "🧺"),
)
SECTION_NAMES = tuple(name for name, _ in SECTION_ORDER)

_RULES = (
    ("Tiefkühl", ("tiefkühl", "tiefkuehl", " tk", "tk ", "frozen")),
    ("Obst & Gemüse", ("tomate", "paprika", "gurke", "kartoff", "zwiebel", "knoblauch", "salat", "möhre", "moehre", "karotte", "zucchini", "brokkoli", "blumenkohl", "apfel", "birne", "banane", "zitrone", "limette", "avocado", "pilz", "champignon", "lauch", "kräuter", "kraeuter", "petersilie", "basilikum", "ingwer", "sellerie", "spinat", "kürbis", "kuerbis", "beere", "traube", "orange", "mandarine")),
    ("Backwaren", ("brot", "brötchen", "broetchen", "baguette", "toast", "wrap", "tortilla", "croissant")),
    ("Fleisch & Fisch", ("fleisch", "hack", "hähn", "haehn", "pute", "rind", "schwein", "wurst", "lachs", "fisch", "garnel", "speck", "schinken", "steak")),
    ("Kühlregal", ("milch", "butter", "joghurt", "quark", "käse", "kaese", "sahne", "creme fraiche", "frischkäse", "frischkaese", "mozzarella", "feta", "ei", "eier", "tofu", "pudding", "margarine")),
    ("Getränke", ("wasser", "saft", "cola", "limonade", "bier", "wein", "energy", "sirup")),
    ("Haushalt & Drogerie", ("spül", "spuel", "reiniger", "papier", "seife", "shampoo", "zahnpasta", "müll", "muell", "waschmittel", "folie", "backpapier", "toilettenpapier", "küchenrolle", "kuechenrolle", "schwamm")),
    ("Trockenwaren", ("nudel", "pasta", "reis", "mehl", "zucker", "salz", "öl", "oel", "essig", "gewürz", "gewuerz", "dose", "bohne", "linse", "kichererb", "tomatenmark", "passierte", "hafer", "müsli", "muesli", "schokolade", "soße", "sosse", "sauce", "brühe", "bruehe", "couscous", "bulgur", "backpulver")),
)

_ALIASES = {
    "eier": "ei", "zwiebeln": "zwiebel", "kartoffeln": "kartoffel",
    "karotten": "karotte", "möhren": "karotte", "moehren": "karotte",
    "knoblauchzehen": "knoblauch", "knoblauchzehe": "knoblauch",
    "champignons": "champignon", "paprikaschoten": "paprika", "paprikaschote": "paprika",
    "tomaten": "tomate", "gurken": "gurke", "zucchinis": "zucchini",
}
_STOPWORDS = {"frisch", "frische", "frischer", "frisches", "klein", "kleine", "kleiner", "groß", "grosse", "große", "großer", "bio"}


def canonical_key(name: str) -> str:
    value = unicodedata.normalize("NFKC", name or "").casefold().replace("ß", "ss")
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9äöü]+", " ", value)
    tokens = []
    for token in value.split():
        token = _ALIASES.get(token, token)
        if token and token not in _STOPWORDS:
            tokens.append(token)
    return " ".join(tokens).strip() or "artikel"


def infer_section(name: str) -> str:
    haystack = f" {name.casefold()} "
    for section, needles in _RULES:
        if any(needle in haystack for needle in needles):
            return section
    return "Sonstiges"


def open_list(session: Session) -> GroceryList:
    row = session.exec(select(GroceryList).where(GroceryList.status == LIST_OPEN).order_by(GroceryList.created_at.desc(), GroceryList.id.desc())).first()
    if row is None:
        row = GroceryList()
        session.add(row)
        session.flush()
    return row


def touch(session: Session, shopping: GroceryList) -> None:
    shopping.revision += 1
    shopping.updated_at = datetime.now()
    session.add(shopping)


def _ids(csv: str | None) -> list[int]:
    values: list[int] = []
    for raw in (csv or "").split(","):
        raw = raw.strip()
        if raw.isdigit() and int(raw) not in values:
            values.append(int(raw))
    return values


def _append_id(csv: str | None, value: int | None) -> str:
    values = _ids(csv)
    if value is not None and value not in values:
        values.append(value)
    return ",".join(map(str, values))


def _rule(session: Session, key: str) -> GroceryItemRule | None:
    return session.exec(select(GroceryItemRule).where(GroceryItemRule.canonical_key == key)).first()


def remember_rule(session: Session, key: str, display_name: str, section: str, priority: int) -> None:
    section = section if section in SECTION_NAMES else "Sonstiges"
    priority = max(-10, min(10, priority))
    row = _rule(session, key)
    if row is None:
        row = GroceryItemRule(canonical_key=key, display_name=display_name, section=section, priority=priority)
    else:
        row.display_name = display_name or row.display_name
        row.section = section
        row.priority = priority
        row.observations += 1
        row.updated_at = datetime.now()
    session.add(row)


def _merge_amount(item: GroceryItem, amount: float | None, unit: str | None) -> bool:
    if amount is None:
        item.uncertain = True
        return True
    if item.amount is None:
        item.amount = amount
        item.unit = units.normalize_unit(unit) or None
        return True
    old = units.to_base(item.amount, item.unit)
    new = units.to_base(amount, unit)
    if old and new and old.dimension == new.dimension:
        merged_amount, merged_unit = units.pretty_base(old.amount + new.amount, old.dimension)
        item.amount = merged_amount
        item.unit = merged_unit or None
        return True
    if units.normalize_unit(item.unit) == units.normalize_unit(unit):
        item.amount = round(item.amount + amount, 3)
        return True
    return False


def add_requirement(session: Session, shopping: GroceryList, *, name: str, amount: float | None, unit: str | None, member_id: int | None, source_kind: str, recipe_id: int | None = None, note: str = "") -> tuple[GroceryItem, bool]:
    display_name = (name or "").strip() or "Unbenannter Artikel"
    key = canonical_key(display_name)
    learned = _rule(session, key)
    candidates = session.exec(select(GroceryItem).where(GroceryItem.list_id == shopping.id).where(GroceryItem.canonical_key == key).where(GroceryItem.state == ITEM_OPEN).order_by(GroceryItem.id)).all()
    for item in candidates:
        if _merge_amount(item, amount, unit):
            item.recipe_ids_csv = _append_id(item.recipe_ids_csv, recipe_id)
            item.contributor_ids_csv = _append_id(item.contributor_ids_csv, member_id)
            item.primary_recipe_id = item.primary_recipe_id or recipe_id
            if source_kind == SOURCE_RECIPE:
                item.source_kind = SOURCE_RECIPE
            if note and note not in item.note:
                item.note = " · ".join(part for part in [item.note, note] if part)
            if learned:
                item.section, item.priority = learned.section, learned.priority
            item.updated_at = datetime.now()
            session.add(item)
            return item, False
    item = GroceryItem(
        list_id=shopping.id, name=display_name, canonical_key=key, amount=amount,
        unit=units.normalize_unit(unit) or None, section=learned.section if learned else infer_section(display_name),
        priority=learned.priority if learned else 0, uncertain=amount is None, note=note,
        source_kind=source_kind, primary_recipe_id=recipe_id,
        recipe_ids_csv=_append_id("", recipe_id), contributor_ids_csv=_append_id("", member_id),
        added_by_member_id=member_id,
    )
    session.add(item)
    session.flush()
    return item, True


def add_recipe_requirements(session: Session, recipe: Recipe, *, servings: int, member_id: int | None) -> dict[str, int]:
    shopping = open_list(session)
    base = max(1, recipe.base_servings or 1)
    target = max(1, servings)
    factor = target / base
    created = merged = 0
    for ingredient in recipe.ingredients:
        _, is_new = add_requirement(
            session, shopping, name=ingredient.name,
            amount=ingredient.amount * factor if ingredient.amount is not None else None,
            unit=ingredient.unit, member_id=member_id, source_kind=SOURCE_RECIPE,
            recipe_id=recipe.id, note=f"Für {recipe.title}",
        )
        created += int(is_new); merged += int(not is_new)
    touch(session, shopping)
    return {"created": created, "merged": merged, "ingredients": len(recipe.ingredients)}


def grouped_rows(session: Session, shopping: GroceryList) -> list[dict]:
    members = {m.id: m for m in session.exec(select(HouseholdMember).where(HouseholdMember.active == True)).all()}  # noqa: E712
    items = list(session.exec(select(GroceryItem).where(GroceryItem.list_id == shopping.id).order_by(GroceryItem.id)).all())
    recipe_ids = sorted({rid for item in items for rid in _ids(item.recipe_ids_csv)})
    recipes = {r.id: r.title for r in (session.exec(select(Recipe).where(Recipe.id.in_(recipe_ids))).all() if recipe_ids else [])}  # type: ignore[attr-defined]
    buckets: dict[str, list[dict]] = {name: [] for name in SECTION_NAMES}
    for item in items:
        if item.section not in SECTION_NAMES:
            item.section = infer_section(item.name)
            session.add(item)
        contributor_ids = _ids(item.contributor_ids_csv)
        if item.added_by_member_id and item.added_by_member_id not in contributor_ids:
            contributor_ids.append(item.added_by_member_id)
        buckets[item.section].append({
            "item": item,
            "sources": [recipes[rid] for rid in _ids(item.recipe_ids_csv) if rid in recipes],
            "contributors": [members[mid] for mid in contributor_ids if mid in members],
            "checked_by": members.get(item.checked_by_member_id),
        })
    result = []
    for section, icon in SECTION_ORDER:
        rows = buckets[section]
        rows.sort(key=lambda row: (row["item"].state == ITEM_BOUGHT, -row["item"].priority, row["item"].name.casefold(), row["item"].id or 0))
        if rows:
            open_count = sum(row["item"].state != ITEM_BOUGHT for row in rows)
            result.append({"name": section, "icon": icon, "rows": rows, "open_count": open_count, "done_count": len(rows) - open_count})
    return result


def summary(groups: Iterable[dict]) -> dict:
    groups = list(groups)
    rows = [row for group in groups for row in group["rows"]]
    remaining = sum(row["item"].state != ITEM_BOUGHT for row in rows)
    bought = len(rows) - remaining
    source_names = Counter(source for row in rows for source in row["sources"])
    next_group = next((g for g in groups if g["open_count"]), None)
    return {
        "total": len(rows), "remaining": remaining, "bought": bought,
        "progress": round((bought / len(rows)) * 100) if rows else 0,
        "shared": sum(len(row["sources"]) > 1 or len(row["contributors"]) > 1 for row in rows),
        "uncertain": sum(row["item"].uncertain and row["item"].state != ITEM_BOUGHT for row in rows),
        "recipes": len(source_names),
        "next_section": next_group["name"] if next_group else None,
        "next_icon": next_group["icon"] if next_group else None,
        "next_count": next_group["open_count"] if next_group else 0,
    }
