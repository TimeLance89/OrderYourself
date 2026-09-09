"""Gerätebezogene Identität für mehrere Personen desselben Haushalts."""
from fastapi import Request, Response
from sqlmodel import Session, select
from app.models import HouseholdMember

COOKIE_NAME = "oy_member"


def ensure_default_member(session: Session) -> HouseholdMember:
    member = session.exec(select(HouseholdMember).where(HouseholdMember.active == True).order_by(HouseholdMember.sort_order, HouseholdMember.id)).first()  # noqa: E712
    if member:
        return member
    member = HouseholdMember(name="Haushalt", icon="🏠")
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def active_members(session: Session) -> list[HouseholdMember]:
    rows = list(session.exec(select(HouseholdMember).where(HouseholdMember.active == True).order_by(HouseholdMember.sort_order, HouseholdMember.name, HouseholdMember.id)).all())  # noqa: E712
    return rows or [ensure_default_member(session)]


def current_member(request: Request, session: Session) -> HouseholdMember:
    raw = (request.cookies.get(COOKIE_NAME) or "").strip()
    if raw.isdigit():
        member = session.get(HouseholdMember, int(raw))
        if member and member.active:
            return member
    return ensure_default_member(session)


def set_member_cookie(response: Response, member: HouseholdMember) -> None:
    response.set_cookie(COOKIE_NAME, str(member.id), max_age=31_536_000, httponly=True, samesite="lax", path="/")
