import re

from services.hf_client import hf_chat
from services.meal_db import meal_db


def parse_ingredients_ru_en(text: str) -> list[str]:
    normalized_text = text.lower().strip()

    for separator in [" и ", ";", "|"]:
        normalized_text = normalized_text.replace(separator, ",")

    raw_parts = [part.strip() for part in normalized_text.split(",") if part.strip()]

    cleaned_parts = []
    for part in raw_parts:
        part = re.sub(r"\d+", "", part)
        part = re.sub(r"\b(г|гр|кг|мл|л|шт|штук)\b", "", part).strip()
        part = re.sub(r"\s+", " ", part)
        if part and part not in cleaned_parts:
            cleaned_parts.append(part)

    russian_to_english = {
        "курица": "chicken",
        "куриная грудка": "chicken",
        "куриное филе": "chicken",
        "рис": "rice",
        "яйцо": "egg",
        "яйца": "egg",
        "сыр": "cheese",
        "пармезан": "cheese",
        "пармезан сыр": "cheese",
        "мука": "flour",
        "хлеб": "bread",
        "яблоко": "apple",
        "яблоки": "apple",
        "банан": "banana",
        "бананы": "banana",
        "йогурт": "yogurt",
        "молоко": "milk",
        "масло": "butter",
        "сливочное масло": "butter",
        "оливковое масло": "olive oil",
        "джем": "jam",
        "черничный джем": "jam",
        "варенье": "jam",
        "творог": "cheese",
        "говядина": "beef",
        "свинина": "pork",
        "рыба": "fish",
        "лук": "onion",
        "чеснок": "garlic",
        "помидор": "tomato",
        "помидоры": "tomato",
        "картошка": "potato",
        "картофель": "potato",
        "макароны": "pasta",
    }

    english_aliases = {
        "blueberry jam": "jam",
        "parmesan cheese": "cheese",
        "protein powder": "protein",
        "eggs": "egg",
        "apples": "apple",
        "bananas": "banana",
    }

    result = []
    for item in cleaned_parts:
        item = russian_to_english.get(item, item)
        item = english_aliases.get(item, item)
        if item not in result:
            result.append(item)

    return result[:15]


def normalize_ingredient_name(value: str) -> str:
    value = value.lower().strip()

    aliases = {
        "eggs": "egg",
        "apples": "apple",
        "bananas": "banana",
        "parmesan cheese": "cheese",
        "blueberry jam": "jam",
    }

    return aliases.get(value, value)


def extract_meal_ingredients(meal: dict) -> list[str]:
    ingredients = []

    for index in range(1, 21):
        ingredient = (meal.get(f"strIngredient{index}") or "").strip().lower()
        if ingredient:
            ingredients.append(normalize_ingredient_name(ingredient))

    return ingredients


def score_meal(user_ingredients: list[str], meal_ingredients: list[str]) -> dict:
    user_ingredient_set = {normalize_ingredient_name(item) for item in user_ingredients}
    meal_ingredient_set = {normalize_ingredient_name(item) for item in meal_ingredients}

    matched = sorted(user_ingredient_set & meal_ingredient_set)
    missing = sorted(meal_ingredient_set - user_ingredient_set)

    score = len(matched)
    coverage = round((len(matched) / len(meal_ingredient_set)) * 100) if meal_ingredient_set else 0

    return {
        "matched": matched,
        "missing": missing,
        "score": score,
        "coverage": coverage,
    }


async def search_meals_by_all_ingredients(ingredients: list[str]) -> list[dict]:
    all_meals = []
    seen_ids = set()

    for ingredient in ingredients:
        try:
            meals = await meal_db.by_ingredient(ingredient)
        except Exception:
            continue

        for meal in meals:
            meal_id = meal.get("idMeal")
            if meal_id and meal_id not in seen_ids:
                seen_ids.add(meal_id)
                all_meals.append(meal)

    return all_meals


async def find_best_meals(user_ingredients: list[str], limit: int = 10) -> list[dict]:
    base_meals = await search_meals_by_all_ingredients(user_ingredients)

    result = []
    for short_meal in base_meals:
        meal_id = short_meal.get("idMeal")
        if not meal_id:
            continue

        try:
            full_meal = await meal_db.details(meal_id)
        except Exception:
            continue

        if not full_meal:
            continue

        meal_ingredients = extract_meal_ingredients(full_meal)
        stats = score_meal(user_ingredients, meal_ingredients)

        if stats["score"] == 0:
            continue

        result.append(
            {
                "id": meal_id,
                "title": full_meal.get("strMeal", "Без названия"),
                "category": full_meal.get("strCategory", ""),
                "area": full_meal.get("strArea", ""),
                "instructions": full_meal.get("strInstructions", ""),
                "ingredients": meal_ingredients,
                "matched": stats["matched"],
                "missing": stats["missing"],
                "score": stats["score"],
                "coverage": stats["coverage"],
            }
        )

    result.sort(key=lambda meal: (meal["score"], meal["coverage"]), reverse=True)
    return result[:limit]


async def generate_menu_from_ingredients(user_ingredients: list[str]) -> str:
    best_meals = await find_best_meals(user_ingredients, limit=10)

    if not best_meals:
        return (
            "Я не нашёл подходящих блюд по этому набору продуктов.\n"
            "Попробуйте указать более базовые ингредиенты, например: курица, рис, яйца, сыр, картофель."
        )

    meal_blocks = []
    for index, meal in enumerate(best_meals, start=1):
        meal_blocks.append(
            f"""Вариант {index}:
Название: {meal["title"]}
Категория: {meal["category"]}
Совпало ингредиентов: {", ".join(meal["matched"]) if meal["matched"] else "нет"}
Не хватает: {", ".join(meal["missing"][:6]) if meal["missing"] else "ничего"}
Процент совпадения: {meal["coverage"]}%
"""
        )

    prompt = f"""
Ты помощник по кулинарии.

Пользователь указал продукты:
{", ".join(user_ingredients)}

Вот найденные варианты блюд:
{chr(10).join(meal_blocks)}

Твоя задача:
1. Проанализировать все продукты пользователя.
2. Выбрать максимально подходящие блюда.
3. По возможности составить:
   - первое
   - второе
   - десерт
4. Если полноценное меню не получается, честно скажи это.
5. Отвечай только на русском.
6. Пиши понятно и по делу.
7. Для каждого блюда укажи:
   - название
   - пошаговый рецепт приготовления
   - что уже есть из продуктов
   - чего не хватает
8. Не выдумывай ингредиенты, которых нет в списке и нет в блоке "Не хватает".
9. В конце предложи лучший вариант меню из имеющихся продуктов.

Формат ответа:
🍽 Что можно приготовить

Первое:
...

Второе:
...

Десерт:
...

Итог:
...
""".strip()

    try:
        return await hf_chat(prompt)
    except Exception:
        lines = ["🍽 Что можно приготовить", ""]
        for meal in best_meals[:5]:
            lines.append(
                f"• {meal['title']} — совпадение {meal['coverage']}%, "
                f"есть: {', '.join(meal['matched']) if meal['matched'] else 'нет'}"
            )
        return "\n".join(lines)