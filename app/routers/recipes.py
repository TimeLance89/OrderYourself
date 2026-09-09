"""Rezepte entdecken, speichern und in den gemeinsamen Einkaufszettel übernehmen."""
from typing import Optional
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select
from app.db import get_session
from app.models import Recipe, RecipeIngredient
from app.services import chefkoch, inspiration
from app.templating import templates

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _book(session: Session) -> list[Recipe]:
    return list(session.exec(select(Recipe).where(Recipe.is_personal == True).order_by(Recipe.imported_at.desc())).all())  # noqa: E712


@router.get("", response_class=HTMLResponse)
def page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "recipes.html", {"categories": inspiration.categories(), "book_count": len(_book(session))})


@router.get("/book", response_class=HTMLResponse)
def book(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "recipe_book.html", {"recipes": _book(session)})


@router.post("/search", response_class=HTMLResponse)
def search(request: Request, query: str = Form(...)):
    try:
        results, error = chefkoch.search(query.strip(), limit=12), None
    except chefkoch.ChefkochError as exc:
        results, error = [], str(exc)
    return templates.TemplateResponse(request, "partials/recipe_search_results.html", {"results": results, "error": error})


@router.get("/inspiration/{slug}", response_class=HTMLResponse)
def category(request: Request, slug: str):
    try:
        results, error = inspiration.results_for(slug) or [], None
    except chefkoch.ChefkochError as exc:
        results, error = [], str(exc)
    return templates.TemplateResponse(request, "partials/recipe_search_results.html", {"results": results, "error": error})


@router.get("/preview/{chefkoch_id}", response_class=HTMLResponse)
def preview(request: Request, chefkoch_id: str, servings: Optional[int] = Query(None), session: Session = Depends(get_session)):
    existing = session.exec(select(Recipe).where(Recipe.chefkoch_id == chefkoch_id)).first()
    if existing:
        return RedirectResponse(f"/recipes/{existing.id}", status_code=303)
    try:
        parsed = chefkoch.parse_recipe(chefkoch.fetch_recipe(chefkoch_id))
    except chefkoch.ChefkochError as exc:
        return HTMLResponse(f"Vorschau nicht möglich: {exc}", status_code=502)
    target = max(1, servings or parsed.base_servings or 1); base = max(1, parsed.base_servings or 1); factor = target / base
    ingredients = [{"group_header": i.group_header, "name": i.name, "amount": i.amount * factor if i.amount is not None else None, "unit": i.unit, "usage_info": i.usage_info} for i in parsed.ingredients]
    return templates.TemplateResponse(request, "recipe_preview.html", {"external_id": chefkoch_id, "title": parsed.title, "subtitle": parsed.subtitle, "image_url": parsed.image_url, "site_url": parsed.site_url, "instructions": parsed.instructions, "base_servings": base, "target_servings": target, "ingredients": ingredients, "rating": parsed.ck_rating, "difficulty_label": chefkoch.difficulty_label(parsed.difficulty), "total_time": parsed.total_time})


def _save_parsed(session: Session, parsed) -> Recipe:
    recipe = Recipe(
        chefkoch_id=parsed.chefkoch_id, title=parsed.title, subtitle=parsed.subtitle,
        base_servings=max(1, parsed.base_servings or 1), image_url=parsed.image_url, site_url=parsed.site_url,
        instructions=parsed.instructions, kcalories=parsed.kcalories, total_time=parsed.total_time,
        ck_rating=parsed.ck_rating, ck_num_votes=parsed.ck_num_votes, difficulty=parsed.difficulty,
        preparation_time=parsed.preparation_time, cooking_time=parsed.cooking_time, resting_time=parsed.resting_time,
        protein_g=parsed.protein_g, fat_g=parsed.fat_g, carbs_g=parsed.carbs_g, cuisine=parsed.cuisine,
        has_video=parsed.has_video, is_premium=parsed.is_premium, tips_html=parsed.tips_html,
        tip_decisive=parsed.tip_decisive, tip_common_errors=parsed.tip_common_errors, tip_appearance=parsed.tip_appearance,
        tags_csv=",".join(parsed.tags), meal_type=parsed.meal_type, is_personal=True,
    )
    for idx, ing in enumerate(parsed.ingredients):
        recipe.ingredients.append(RecipeIngredient(sort_index=idx, group_header=ing.group_header, name=ing.name, amount=ing.amount, unit=ing.unit, usage_info=ing.usage_info, is_basic=ing.is_basic, source_raw_line=ing.source_raw_line, source_amount_raw=ing.source_amount_raw, parse_status=ing.parse_status, parse_error=ing.parse_error))
    session.add(recipe); session.commit(); session.refresh(recipe)
    return recipe


@router.post("/import")
def import_recipe(recipe_ref: str = Form(...), session: Session = Depends(get_session)):
    chefkoch_id = chefkoch.extract_recipe_id(recipe_ref)
    if not chefkoch_id:
        return HTMLResponse("Ungültige Rezept-ID oder URL.", status_code=400)
    existing = session.exec(select(Recipe).where(Recipe.chefkoch_id == chefkoch_id)).first()
    if existing:
        existing.is_personal = True; session.add(existing); session.commit()
        return RedirectResponse(f"/recipes/{existing.id}", status_code=303)
    try:
        parsed = chefkoch.parse_recipe(chefkoch.fetch_recipe(chefkoch_id))
    except chefkoch.ChefkochError as exc:
        return HTMLResponse(f"Import fehlgeschlagen: {exc}", status_code=502)
    recipe = _save_parsed(session, parsed)
    return RedirectResponse(f"/recipes/{recipe.id}", status_code=303)


@router.get("/{recipe_id}", response_class=HTMLResponse)
def detail(request: Request, recipe_id: int, servings: Optional[int] = Query(None), session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        return HTMLResponse("Rezept nicht gefunden.", status_code=404)
    target = max(1, servings or recipe.base_servings or 1); factor = target / max(1, recipe.base_servings or 1)
    ingredients = [{"group_header": i.group_header, "name": i.name, "amount": i.amount * factor if i.amount is not None else None, "unit": i.unit, "usage_info": i.usage_info} for i in recipe.ingredients]
    return templates.TemplateResponse(request, "recipe_detail.html", {"recipe": recipe, "target_servings": target, "ingredients": ingredients, "difficulty_label": chefkoch.difficulty_label(recipe.difficulty)})


@router.post("/{recipe_id}/delete")
def delete(recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if recipe:
        session.delete(recipe); session.commit()
    return RedirectResponse("/recipes/book", status_code=303)
