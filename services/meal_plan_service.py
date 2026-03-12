from dataclasses import dataclass

from bot_data.state import MealState
from services.hf_client import hf_chat


@dataclass
class MealTargets:
    bmr_calories: int
    maintenance_calories: int
    target_calories: int
    protein_grams: int
    fat_grams: int
    carbohydrate_grams: int
    lean_body_mass_kilograms: float | None = None


def calculate_bmr(state: MealState) -> float:
    if state.sex not in {"male", "female"}:
        raise ValueError("Не указан пол")

    if state.age is None or state.height_in_centimeters is None or state.weight_in_kilograms is None:
        raise ValueError("Недостаточно данных для расчёта BMR")

    base_value = (
        10 * state.weight_in_kilograms
        + 6.25 * state.height_in_centimeters
        - 5 * state.age
    )

    if state.sex == "male":
        return base_value + 5

    return base_value - 161


def calculate_lean_body_mass(state: MealState) -> float | None:
    if state.body_fat_percent is None:
        return None

    return state.weight_in_kilograms * (1 - state.body_fat_percent / 100)


def calculate_meal_targets(state: MealState) -> MealTargets:
    if state.goal not in {"fatloss", "bulk", "maintain"}:
        raise ValueError("Не указана цель питания")

    if state.weight_in_kilograms is None:
        raise ValueError("Не указан вес")

    bmr_calories = calculate_bmr(state)

    activity_multiplier = 1.45
    maintenance_calories = round(bmr_calories * activity_multiplier)

    lean_body_mass_kilograms = calculate_lean_body_mass(state)

    if state.goal == "fatloss":
        target_calories = round(maintenance_calories * 0.85)

        if lean_body_mass_kilograms is not None:
            protein_grams = round(lean_body_mass_kilograms * 2.5)
        else:
            protein_grams = round(state.weight_in_kilograms * 2.0)

    elif state.goal == "bulk":
        target_calories = round(maintenance_calories * 1.10)
        protein_grams = round(state.weight_in_kilograms * 1.8)

    else:
        target_calories = maintenance_calories
        protein_grams = round(state.weight_in_kilograms * 1.8)

    fat_grams = round(state.weight_in_kilograms * 0.8)

    carbohydrate_calories = target_calories - protein_grams * 4 - fat_grams * 9
    carbohydrate_grams = round(carbohydrate_calories / 4)

    if carbohydrate_grams < 50:
        carbohydrate_grams = 50
        target_calories = protein_grams * 4 + fat_grams * 9 + carbohydrate_grams * 4

    return MealTargets(
        bmr_calories=round(bmr_calories),
        maintenance_calories=maintenance_calories,
        target_calories=target_calories,
        protein_grams=protein_grams,
        fat_grams=fat_grams,
        carbohydrate_grams=carbohydrate_grams,
        lean_body_mass_kilograms=lean_body_mass_kilograms,
    )


def build_meal_plan_prompt(state: MealState, targets: MealTargets) -> str:
    sex_name_map = {
        "male": "мужчина",
        "female": "женщина",
    }
    goal_name_map = {
        "fatloss": "похудение",
        "bulk": "набор массы",
        "maintain": "поддержание",
    }
    restriction_name_map = {
        "nodairy": "без молочного",
        "nomeat": "без мяса",
        "nogluten": "без глютена",
        "none": "без ограничений",
    }

    body_fat_text = (
        f"{state.body_fat_percent}%"
        if state.body_fat_percent is not None
        else "неизвестен"
    )

    lean_body_mass_text = (
        f"{round(targets.lean_body_mass_kilograms, 1)} кг"
        if targets.lean_body_mass_kilograms is not None
        else "не рассчитана"
    )

    return f"""
Ты спортивный нутрициолог. Составь недельный план питания на 7 дней.

Данные клиента:
- пол: {sex_name_map.get(state.sex, state.sex)}
- возраст: {state.age}
- рост: {state.height_in_centimeters} см
- вес: {state.weight_in_kilograms} кг
- процент жира: {body_fat_text}
- безжировая масса: {lean_body_mass_text}
- цель: {goal_name_map.get(state.goal, state.goal)}
- ограничения: {restriction_name_map.get(state.restriction, state.restriction)}

Рассчитанные ориентиры:
- базовый обмен: {targets.bmr_calories} ккал
- поддержание: {targets.maintenance_calories} ккал
- целевые калории: {targets.target_calories} ккал
- белок: {targets.protein_grams} г
- жиры: {targets.fat_grams} г
- углеводы: {targets.carbohydrate_grams} г

Главные правила:
1. Составь план питания на 7 дней.
2. Для каждого дня укажи:
   - завтрак
   - обед
   - ужин
   - 1 перекус
3. Основа плана должна соответствовать целевым калориям и макросам.
4. Белок должен быть распределён по дню, а не собран в одном приёме пищи.
5. Не используй markdown-таблицы.
6. Пиши только на русском.
7. Без длинной теории и воды.
8. Используй простые, доступные и обычные продукты.
9. Не используй дорогие, редкие или экзотические продукты без необходимости.
10. Допускается повторение продуктов и блюд в разные дни.
11. Не используй спортивные добавки без необходимости.
12. Не давай странные универсальные советы вроде "пейте 8 литров воды".
13. Если цель похудение, блюда должны быть сытными и умеренно низкокалорийными.
14. Если цель набор массы, увеличь калорийность аккуратно, без превращения рациона в фастфуд.
15. Если цель поддержание, сделай рацион сбалансированным.
16. Не нужно делать каждый день полностью уникальным и сложным.
17. Отдавай предпочтение таким продуктам:
овсянка, яйца, курица, индейка, творог, йогурт, рис, гречка, макароны, картофель, овощи, фрукты, рыба, сыр, хлеб, фасоль.
18. Старайся указывать понятные бытовые блюда.
19. Если пишешь примерные итоги, они должны быть близки к целевым значениям.

Формат строго:

День 1:
- Завтрак: ...
- Обед: ...
- Ужин: ...
- Перекус: ...

День 2:
...

День 7:
...

Итог:
- Калории: ...
- Белок: ...
- Жиры: ...
- Углеводы: ...
- Комментарий: ...
""".strip()


async def generate_meal_plan(state: MealState) -> tuple[MealTargets, str]:
    targets = calculate_meal_targets(state)
    prompt = build_meal_plan_prompt(state, targets)
    response_text = await hf_chat(prompt, max_tokens=2500)
    return targets, response_text