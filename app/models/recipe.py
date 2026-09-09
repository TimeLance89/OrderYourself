"""Importiertes Chefkoch-Rezept + strukturierte Zutaten (Phase 2)."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Recipe(SQLModel, table=True):
    """Ein aus Chefkoch importiertes Rezept (Rohantwort im Cache-Feld)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    chefkoch_id: str = Field(index=True, unique=True)
    title: str
    subtitle: Optional[str] = None
    base_servings: int = Field(default=1)  # `servings` aus der API
    image_url: Optional[str] = None
    site_url: str = ""
    instructions: Optional[str] = None
    kcalories: Optional[int] = None
    total_time: Optional[int] = None  # Minuten
    imported_at: datetime = Field(default_factory=datetime.now)
    cached_json: Optional[str] = None  # Roh-Antwort (Cache/Nachvollziehbarkeit)

    # Chefkoch-Zusatzdaten (Rezepte-Vielfalt): Community-Bewertung (getrennt
    # von der eigenen Bewertung aus Phase 12), Schwierigkeit, Zeiten-
    # Aufschlüsselung, Nährwerte, Herkunft, Video/Premium-Flags, redaktionelle
    # Chefkoch-Tipps, freie Tags + daraus abgeleiteter Mahlzeiten-Typ.
    ck_rating: Optional[float] = None
    ck_num_votes: int = Field(default=0)
    difficulty: Optional[int] = None  # 1 (einfach) .. 3 (anspruchsvoll)
    preparation_time: Optional[int] = None  # Minuten
    cooking_time: Optional[int] = None
    resting_time: Optional[int] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    carbs_g: Optional[float] = None
    cuisine: Optional[str] = None
    has_video: bool = Field(default=False)
    is_premium: bool = Field(default=False)
    tips_html: Optional[str] = None
    tip_decisive: Optional[str] = None
    tip_common_errors: Optional[str] = None
    tip_appearance: Optional[str] = None
    tags_csv: Optional[str] = None  # komma-getrennt, siehe `tag_list()`
    meal_type: Optional[str] = Field(default=None, index=True)

    # Monsieur-Cuisine-Smart-Rezeptbuch: `chefkoch_id` bleibt Pflichtfeld+unique
    # (Schema nicht angefasst) — MC-Importe bekommen dort `f"mc-{mc_id}"` als
    # eindeutigen Platzhalter, die echte numerische ID steht separat in `mc_id`
    # (kein DB-Unique-Constraint nötig, Dublettencheck per Query vor dem Insert,
    # gleiches Muster wie `Product.gtin`).
    source: str = Field(default="chefkoch", index=True)  # "chefkoch" | "mc_smart"
    # Mitgliedschaft in „Meine Rezepte“. Automatisch für einen Plan geladene
    # Katalogrezepte bleiben False; bewusste Browser-Importe sind True.
    is_personal: bool = Field(default=True, index=True)
    mc_id: Optional[str] = Field(default=None, index=True)
    serving_unit: Optional[str] = None  # z. B. "Gläser" — None = "Portion(en)"

    def tag_list(self) -> list[str]:
        return [t for t in (self.tags_csv or "").split(",") if t]

    ingredients: list["RecipeIngredient"] = Relationship(
        back_populates="recipe",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "RecipeIngredient.sort_index",
        },
    )


class RecipeIngredient(SQLModel, table=True):
    """Eine Zutat eines Rezepts, strukturiert (Basis-Portionen = recipe.base_servings)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key="recipe.id", index=True)
    sort_index: int = Field(default=0)

    group_header: Optional[str] = None  # z. B. „Für die Füllung"
    name: str
    amount: Optional[float] = None  # bezogen auf base_servings
    unit: Optional[str] = None
    usage_info: Optional[str] = None  # „(Größe M)", „, fettarme"
    is_basic: bool = Field(default=False)  # Chefkochs „Grundzutat"-Flag

    # Unveränderte Quellangabe und Parserdiagnose. Damit kann die
    # Einkaufsliste unterscheiden, ob eine Menge bereits in der Quelle fehlte
    # oder beim Einlesen nicht verstanden wurde.
    source_raw_line: Optional[str] = None
    source_amount_raw: Optional[str] = None
    parse_status: str = Field(default="legacy", index=True)
    parse_error: Optional[str] = None

    recipe: Optional["Recipe"] = Relationship(back_populates="ingredients")
