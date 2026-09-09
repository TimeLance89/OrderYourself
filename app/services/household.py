from sqlmodel import Session, select
from app.models import HouseholdEvent, HouseholdProfile


def get_or_create_profile(session: Session) -> HouseholdProfile:
    row = session.exec(select(HouseholdProfile).order_by(HouseholdProfile.id)).first()
    if row is None:
        row = HouseholdProfile()
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def log_event(session: Session, kind: str, title: str, detail: str = "", actor_member_id: int | None = None) -> None:
    actor_detail = f"Mitglied #{actor_member_id}" if actor_member_id else ""
    combined = " · ".join(part for part in [detail, actor_detail] if part)
    session.add(HouseholdEvent(kind=kind, title=title, detail=combined, source="web"))


def recent_events(session: Session, limit: int = 20):
    return list(session.exec(select(HouseholdEvent).order_by(HouseholdEvent.at.desc()).limit(limit)).all())
