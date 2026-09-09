from sqlmodel import Session, SQLModel, create_engine, select
from app.models import GroceryItem, HouseholdMember, Recipe, RecipeIngredient
from app.services.smart_shopping import add_recipe_requirements, add_requirement, canonical_key, grouped_rows, infer_section, open_list, remember_rule
from app.models.shopping import SOURCE_MANUAL


def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_aliases_and_store_sections():
    assert canonical_key("frische Möhren") == "karotte"
    assert canonical_key("Knoblauchzehen") == "knoblauch"
    assert infer_section("500 g Hähnchenbrust") == "Fleisch & Fisch"
    assert infer_section("TK Beeren") == "Tiefkühl"


def test_compatible_amounts_are_merged_and_contributors_preserved():
    with session() as s:
        a = HouseholdMember(name="A"); b = HouseholdMember(name="B")
        s.add(a); s.add(b); s.commit(); s.refresh(a); s.refresh(b)
        shopping = open_list(s)
        add_requirement(s, shopping, name="Tomaten", amount=500, unit="g", member_id=a.id, source_kind=SOURCE_MANUAL)
        add_requirement(s, shopping, name="Tomate", amount=1, unit="kg", member_id=b.id, source_kind=SOURCE_MANUAL)
        s.commit()
        rows = s.exec(select(GroceryItem)).all()
        assert len(rows) == 1
        assert rows[0].amount == 1.5
        assert rows[0].unit == "kg"
        assert set(rows[0].contributor_ids_csv.split(",")) == {str(a.id), str(b.id)}


def test_recipe_requirements_merge_across_recipes_and_keep_sources():
    with session() as s:
        member = HouseholdMember(name="Steffen"); s.add(member); s.commit(); s.refresh(member)
        r1 = Recipe(chefkoch_id="a", title="A", base_servings=2)
        r1.ingredients.append(RecipeIngredient(name="Zwiebeln", amount=2, unit="Stück"))
        r2 = Recipe(chefkoch_id="b", title="B", base_servings=2)
        r2.ingredients.append(RecipeIngredient(name="Zwiebel", amount=1, unit="Stück"))
        s.add(r1); s.add(r2); s.commit(); s.refresh(r1); s.refresh(r2)
        add_recipe_requirements(s, r1, servings=2, member_id=member.id)
        add_recipe_requirements(s, r2, servings=2, member_id=member.id)
        s.commit()
        item = s.exec(select(GroceryItem)).one()
        assert item.amount == 3
        assert set(item.recipe_ids_csv.split(",")) == {str(r1.id), str(r2.id)}
        groups = grouped_rows(s, open_list(s))
        assert groups[0]["name"] == "Obst & Gemüse"
        assert groups[0]["rows"][0]["sources"] == ["A", "B"]


def test_manual_section_correction_is_learned():
    with session() as s:
        shopping = open_list(s)
        item, _ = add_requirement(s, shopping, name="Spezialartikel", amount=1, unit="Stück", member_id=None, source_kind=SOURCE_MANUAL)
        remember_rule(s, item.canonical_key, item.name, "Kühlregal", 5)
        s.commit()
        shopping.status = "closed"; s.add(shopping); s.commit()
        next_list = open_list(s)
        next_item, _ = add_requirement(s, next_list, name="Spezialartikel", amount=1, unit="Stück", member_id=None, source_kind=SOURCE_MANUAL)
        assert next_item.section == "Kühlregal"
        assert next_item.priority == 5
