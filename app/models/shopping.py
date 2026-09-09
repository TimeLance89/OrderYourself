"""Händlerunabhängiger gemeinsamer Einkaufszettel."""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

LIST_OPEN = "open"
ITEM_OPEN = "open"
ITEM_BOUGHT = "bought"
SOURCE_MANUAL = "manual"
SOURCE_RECIPE = "recipe"


class GroceryList(SQLModel, table=True):
    __tablename__ = "grocery_list"
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default=LIST_OPEN, index=True)
    revision: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)


class GroceryItem(SQLModel, table=True):
    __tablename__ = "grocery_item"
    id: Optional[int] = Field(default=None, primary_key=True)
    list_id: int = Field(foreign_key="grocery_list.id", index=True)
    name: str
    canonical_key: str = Field(index=True)
    amount: Optional[float] = None
    unit: Optional[str] = None
    section: str = Field(default="Sonstiges", index=True)
    priority: int = Field(default=0, index=True)
    state: str = Field(default=ITEM_OPEN, index=True)
    uncertain: bool = Field(default=False)
    note: str = Field(default="")
    source_kind: str = Field(default=SOURCE_MANUAL, index=True)
    primary_recipe_id: Optional[int] = Field(default=None, foreign_key="recipe.id", index=True)
    recipe_ids_csv: str = Field(default="")
    contributor_ids_csv: str = Field(default="")
    added_by_member_id: Optional[int] = Field(default=None, foreign_key="householdmember.id", index=True)
    checked_by_member_id: Optional[int] = Field(default=None, foreign_key="householdmember.id", index=True)
    checked_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)


class GroceryItemRule(SQLModel, table=True):
    __tablename__ = "grocery_item_rule"
    id: Optional[int] = Field(default=None, primary_key=True)
    canonical_key: str = Field(index=True, unique=True)
    display_name: str = Field(default="")
    section: str = Field(default="Sonstiges", index=True)
    priority: int = Field(default=0)
    observations: int = Field(default=1)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)
