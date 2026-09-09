"""Haushaltsprofil, Mitglieder und Ereignisjournal."""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class HouseholdProfile(SQLModel, table=True):
    """Kompatibel zum bisherigen lokalen Profil, ohne externe Anbieterlogik."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="Mein Haushalt")
    member_count: int = Field(default=1)
    children_count: int = Field(default=0)
    dietary_styles: str = Field(default="")
    allergies: str = Field(default="")
    dislikes: str = Field(default="")
    favorites: str = Field(default="")
    weekday_max_minutes: int = Field(default=35)
    weekend_max_minutes: int = Field(default=75)
    meals_per_week: int = Field(default=5)
    leftover_preference: str = Field(default="gelegentlich")
    variety_preference: int = Field(default=70)
    mc_smart_owned: bool = Field(default=False)
    onboarding_complete: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class HouseholdMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    icon: str = Field(default="🙂")
    active: bool = Field(default=True, index=True)
    sort_order: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class HouseholdEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    at: datetime = Field(default_factory=datetime.now, index=True)
    kind: str = Field(index=True)
    title: str
    detail: str = Field(default="")
    source: str = Field(default="system")
    reference_type: str = Field(default="")
    reference_id: Optional[int] = Field(default=None, index=True)
