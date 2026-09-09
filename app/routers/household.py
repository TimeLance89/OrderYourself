from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session
from app.db import get_session
from app.models import HouseholdMember
from app.services.household import get_or_create_profile, log_event, recent_events
from app.services.household_members import active_members, current_member, set_member_cookie
from app.templating import templates

router = APIRouter(prefix="/household", tags=["household"])


def _context(request, session, saved=False):
    return {"profile": get_or_create_profile(session), "members": active_members(session), "current_member": current_member(request, session), "events": recent_events(session), "saved": saved}


@router.get("", response_class=HTMLResponse)
def page(request: Request, saved: bool = False, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "household.html", _context(request, session, saved))


@router.post("/members")
def add_member(request: Request, name: str = Form(...), icon: str = Form("🙂"), session: Session = Depends(get_session)):
    clean = name.strip()
    if clean:
        member = HouseholdMember(name=clean[:60], icon=(icon.strip() or "🙂")[:8], sort_order=len(active_members(session)))
        session.add(member); session.flush(); log_event(session, "member", f"{member.name} hinzugefügt", actor_member_id=current_member(request, session).id); session.commit()
    return RedirectResponse("/household", status_code=303)


@router.post("/members/{member_id}/select")
def select_member(member_id: int, session: Session = Depends(get_session)):
    response = RedirectResponse("/household", status_code=303)
    member = session.get(HouseholdMember, member_id)
    if member and member.active: set_member_cookie(response, member)
    return response


@router.post("/members/{member_id}/disable")
def disable_member(member_id: int, request: Request, session: Session = Depends(get_session)):
    member = session.get(HouseholdMember, member_id)
    if member and len(active_members(session)) > 1:
        member.active = False; member.updated_at = datetime.now(); session.add(member); log_event(session, "member", f"{member.name} deaktiviert", actor_member_id=current_member(request, session).id); session.commit()
    response = RedirectResponse("/household", status_code=303)
    fallback = current_member(request, session)
    if fallback.id != member_id: set_member_cookie(response, fallback)
    return response


@router.post("/save")
def save_profile(request: Request, name: str = Form("Mein Haushalt"), dietary_styles: str = Form(""), allergies: str = Form(""), dislikes: str = Form(""), favorites: str = Form(""), weekday_max_minutes: int = Form(35), variety_preference: int = Form(70), session: Session = Depends(get_session)):
    row = get_or_create_profile(session)
    row.name = name.strip() or "Mein Haushalt"; row.dietary_styles = dietary_styles.strip(); row.allergies = allergies.strip(); row.dislikes = dislikes.strip(); row.favorites = favorites.strip(); row.weekday_max_minutes = max(10, min(240, weekday_max_minutes)); row.variety_preference = max(0, min(100, variety_preference)); row.updated_at = datetime.now(); session.add(row)
    log_event(session, "profile", "Haushaltsprofil aktualisiert", actor_member_id=current_member(request, session).id); session.commit()
    return RedirectResponse("/household?saved=true", status_code=303)
