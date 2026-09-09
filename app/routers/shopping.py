"""Mehrbenutzerfähiger, händlerunabhängiger Einkaufszettel."""
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select
from app.db import get_session
from app.models import GroceryItem, GroceryList, Recipe
from app.models.shopping import ITEM_BOUGHT, ITEM_OPEN, SOURCE_MANUAL
from app.services.household_members import active_members, current_member
from app.services.smart_shopping import SECTION_NAMES, add_recipe_requirements, add_requirement, canonical_key, grouped_rows, infer_section, open_list, remember_rule, summary, touch
from app.templating import templates

router = APIRouter(prefix="/shopping", tags=["shopping"])


def _context(request: Request, session: Session, message: str | None = None):
    shopping = open_list(session); groups = grouped_rows(session, shopping)
    return {"shopping": shopping, "groups": groups, "summary": summary(groups), "members": active_members(session), "current_member": current_member(request, session), "sections": SECTION_NAMES, "message": message}


def _response(request: Request, session: Session, message: str | None = None):
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/smart_shopping_content.html", _context(request, session, message))
    return RedirectResponse("/shopping", status_code=303)


@router.get("", response_class=HTMLResponse)
def page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "shopping.html", _context(request, session))


@router.get("/content", response_class=HTMLResponse)
def content(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "partials/smart_shopping_content.html", _context(request, session))


@router.post("/manual")
def manual(request: Request, name: str = Form(...), amount: float | None = Form(None), unit: str = Form(""), note: str = Form(""), session: Session = Depends(get_session)):
    member = current_member(request, session); shopping = open_list(session)
    add_requirement(session, shopping, name=name, amount=amount, unit=unit, member_id=member.id, source_kind=SOURCE_MANUAL, note=note.strip())
    touch(session, shopping); session.commit()
    return _response(request, session, f"{name.strip()} hinzugefügt")


@router.post("/from-recipe/{recipe_id}")
def from_recipe(recipe_id: int, request: Request, servings: int | None = Form(None), session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        return HTMLResponse("Rezept nicht gefunden.", status_code=404)
    member = current_member(request, session); result = add_recipe_requirements(session, recipe, servings=max(1, servings or recipe.base_servings or 1), member_id=member.id); session.commit()
    if request.headers.get("HX-Request"):
        return HTMLResponse(f'<span class="inline-success">✓ {recipe.title}: {result["created"]} neu, {result["merged"]} gebündelt</span>')
    return RedirectResponse("/shopping", status_code=303)


@router.post("/items/{item_id}/toggle")
def toggle(item_id: int, request: Request, session: Session = Depends(get_session)):
    item = session.get(GroceryItem, item_id)
    if item:
        shopping = session.get(GroceryList, item.list_id)
        if item.state == ITEM_BOUGHT:
            item.state = ITEM_OPEN; item.checked_at = None; item.checked_by_member_id = None
        else:
            member = current_member(request, session); item.state = ITEM_BOUGHT; item.checked_at = datetime.now(); item.checked_by_member_id = member.id
        item.updated_at = datetime.now(); session.add(item)
        if shopping: touch(session, shopping)
        session.commit()
    return _response(request, session)


@router.post("/items/{item_id}/update")
def update(item_id: int, request: Request, name: str = Form(...), amount: float | None = Form(None), unit: str = Form(""), section: str = Form(""), priority: int = Form(0), note: str = Form(""), session: Session = Depends(get_session)):
    item = session.get(GroceryItem, item_id)
    if item:
        old_list = session.get(GroceryList, item.list_id)
        item.name = name.strip() or item.name; item.canonical_key = canonical_key(item.name); item.amount = amount; item.unit = unit.strip() or None; item.section = section if section in SECTION_NAMES else infer_section(item.name); item.priority = max(-10, min(10, priority)); item.note = note.strip(); item.uncertain = amount is None; item.updated_at = datetime.now(); session.add(item)
        remember_rule(session, item.canonical_key, item.name, item.section, item.priority)
        if old_list: touch(session, old_list)
        session.commit()
    return _response(request, session, "Sortierung für spätere Einkäufe gemerkt")


@router.post("/items/{item_id}/delete")
def delete(item_id: int, request: Request, session: Session = Depends(get_session)):
    item = session.get(GroceryItem, item_id)
    if item:
        shopping = session.get(GroceryList, item.list_id); session.delete(item)
        if shopping: touch(session, shopping)
        session.commit()
    return _response(request, session)


@router.post("/clear-bought")
def clear_bought(request: Request, session: Session = Depends(get_session)):
    shopping = open_list(session)
    rows = session.exec(select(GroceryItem).where(GroceryItem.list_id == shopping.id).where(GroceryItem.state == ITEM_BOUGHT)).all()
    for row in rows: session.delete(row)
    if rows: touch(session, shopping)
    session.commit()
    return _response(request, session)
