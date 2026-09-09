from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from app.db import get_session
from app.models import Recipe
from app.services.household_members import current_member
from app.services.smart_shopping import grouped_rows, open_list, summary
from app.templating import templates

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    shopping = open_list(session); groups = grouped_rows(session, shopping)
    recipes = list(session.exec(select(Recipe).where(Recipe.is_personal == True).order_by(Recipe.imported_at.desc()).limit(5)).all())  # noqa: E712
    return templates.TemplateResponse(request, "dashboard.html", {"current_member": current_member(request, session), "shopping_summary": summary(groups), "shopping_groups": groups[:3], "recent_recipes": recipes})
