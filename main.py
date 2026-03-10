import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from openai import OpenAI




load_dotenv(Path(__file__).with_name(".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN не найден в .env")



HF_BASE_URL = "https://router.huggingface.co/v1"
HF_CHAT_MODEL = "katanemo/Arch-Router-1.5B:hf-inference"

hf_client = OpenAI(base_url=HF_BASE_URL, api_key=HF_TOKEN)


async def hf_chat(prompt: str, max_tokens: int = 800) -> str:
    def call() -> str:
        resp = hf_client.chat.completions.create(
            model=HF_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    return await asyncio.to_thread(call)



class MealDB:
    BASE = "https://www.themealdb.com/api/json/v1/1"

    async def by_ingredient(self, ingredient: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.BASE}/filter.php", params={"i": ingredient})
            r.raise_for_status()
            return (r.json().get("meals") or [])

    async def details(self, meal_id: str) -> dict | None:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.BASE}/lookup.php", params={"i": meal_id})
            r.raise_for_status()
            meals = r.json().get("meals") or []
            return meals[0] if meals else None


mealdb = MealDB()



text_start = "Привет, чем могу помочь?"

text_make_training_plan = "Составить план тренировок"
text_training_plan_started = "Сейчас составим план тренировок"

text_make_meal_plan = "Составить план питания"
text_meal_plan_started = "Сейчас составим план питания"

text_find_recipe = "Найти рецепт"
text_find_recipe_started = "Сейчас подберём блюда по вашим продуктам"

text_input_placeholder = "Выберите действие"




main_menu_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=text_make_training_plan),
            KeyboardButton(text=text_make_meal_plan),
        ],
        [
            KeyboardButton(text=text_find_recipe),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder=text_input_placeholder,
)




def kb_main():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏋️ План тренировок", callback_data="m:workout")
    kb.button(text="🍽️ План питания", callback_data="m:meal")
    kb.button(text="🥘 Рецепты", callback_data="m:recipes")
    kb.adjust(1)
    return kb.as_markup()


def kb_back():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data="m:back")
    return kb.as_markup()


def kb_w_goal():
    kb = InlineKeyboardBuilder()
    kb.button(text="💪 Сила", callback_data="w:goal:strength")
    kb.button(text="🔥 Похудение", callback_data="w:goal:fatloss")
    kb.button(text="🏃 Выносливость", callback_data="w:goal:endurance")
    kb.adjust(1)
    return kb.as_markup()


def kb_w_level():
    kb = InlineKeyboardBuilder()
    kb.button(text="🌱 Новичок", callback_data="w:level:beginner")
    kb.button(text="⚡ Средний", callback_data="w:level:intermediate")
    kb.adjust(2)
    return kb.as_markup()


def kb_days_1_7(prefix: str):
    kb = InlineKeyboardBuilder()
    for d in range(1, 8):
        kb.button(text=str(d), callback_data=f"{prefix}:{d}")
    kb.adjust(4, 3)
    return kb.as_markup()


def kb_w_inventory():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Дом", callback_data="w:eq:home")
    kb.button(text="🏟️ Зал", callback_data="w:eq:gym")
    kb.adjust(2)
    return kb.as_markup()


def kb_p_goal():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔥 Похудение", callback_data="p:goal:fatloss")
    kb.button(text="➕ Набор", callback_data="p:goal:bulk")
    kb.button(text="⚖️ Поддержание", callback_data="p:goal:maintain")
    kb.adjust(1)
    return kb.as_markup()


def kb_p_restrictions():
    kb = InlineKeyboardBuilder()
    kb.button(text="🥛 Без молочного", callback_data="p:res:nodairy")
    kb.button(text="🥩 Без мяса", callback_data="p:res:nomeat")
    kb.button(text="🌾 Без глютена", callback_data="p:res:nogluten")
    kb.button(text="✅ Без ограничений", callback_data="p:res:none")
    kb.adjust(2, 2)
    return kb.as_markup()




user_mode: dict[int, str] = {}


@dataclass
class WorkoutState:
    goal: str | None = None
    level: str | None = None
    days: int | None = None
    eq: str | None = None


@dataclass
class MealState:
    goal: str | None = None
    days: int | None = None
    restriction: str | None = None


workout_state: dict[int, WorkoutState] = {}
meal_state: dict[int, MealState] = {}




bot = Bot(BOT_TOKEN)
dp = Dispatcher()




async def drop_kb(call: CallbackQuery):
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


def reset_user_state(uid: int):
    user_mode.pop(uid, None)
    workout_state.pop(uid, None)
    meal_state.pop(uid, None)


def parse_ingredients_ru_en(text: str) -> list[str]:
    t = text.lower().strip()

    for sep in [" и ", ";", "|"]:
        t = t.replace(sep, ",")

    parts = [p.strip() for p in t.split(",") if p.strip()]

    cleaned = []
    for p in parts:
        p = re.sub(r"\d+", "", p)
        p = re.sub(r"\b(г|гр|кг|мл|л|шт|штук)\b", "", p).strip()
        p = re.sub(r"\s+", " ", p)
        if p and p not in cleaned:
            cleaned.append(p)

    ru2en = {
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

    en_aliases = {
        "blueberry jam": "jam",
        "parmesan cheese": "cheese",
        "protein powder": "protein",
        "eggs": "egg",
        "apples": "apple",
        "bananas": "banana",
    }

    result = []
    for item in cleaned:
        item = ru2en.get(item, item)
        item = en_aliases.get(item, item)
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
    result = []
    for i in range(1, 21):
        ing = (meal.get(f"strIngredient{i}") or "").strip().lower()
        if ing:
            result.append(normalize_ingredient_name(ing))
    return result


def score_meal(user_ingredients: list[str], meal_ingredients: list[str]) -> dict:
    user_set = {normalize_ingredient_name(i) for i in user_ingredients}
    meal_set = {normalize_ingredient_name(i) for i in meal_ingredients}

    matched = sorted(user_set & meal_set)
    missing = sorted(meal_set - user_set)

    score = len(matched)
    coverage = round((len(matched) / len(meal_set)) * 100) if meal_set else 0

    return {
        "matched": matched,
        "missing": missing,
        "score": score,
        "coverage": coverage,
    }


async def search_meals_by_all_ingredients(ingredients: list[str]) -> list[dict]:
    all_meals = []
    seen_ids = set()

    for ing in ingredients:
        try:
            meals = await mealdb.by_ingredient(ing)
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
    for meal_short in base_meals:
        meal_id = meal_short.get("idMeal")
        if not meal_id:
            continue

        try:
            full_meal = await mealdb.details(meal_id)
        except Exception:
            continue

        if not full_meal:
            continue

        meal_ingredients = extract_meal_ingredients(full_meal)
        stats = score_meal(user_ingredients, meal_ingredients)

        if stats["score"] == 0:
            continue

        result.append({
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
        })

    result.sort(key=lambda x: (x["score"], x["coverage"]), reverse=True)
    return result[:limit]


async def generate_menu_from_ingredients(user_ingredients: list[str]) -> str:
    best_meals = await find_best_meals(user_ingredients, limit=10)

    if not best_meals:
        return (
            "Я не нашёл подходящих блюд по этому набору продуктов.\n"
            "Попробуйте указать более базовые ингредиенты, например: курица, рис, яйца, сыр, картофель."
        )

    meals_text_blocks = []
    for idx, meal in enumerate(best_meals, start=1):
        meals_text_blocks.append(
            f"""Вариант {idx}:
Название: {meal['title']}
Категория: {meal['category']}
Совпало ингредиентов: {", ".join(meal['matched']) if meal['matched'] else "нет"}
Не хватает: {", ".join(meal['missing'][:6]) if meal['missing'] else "ничего"}
Процент совпадения: {meal['coverage']}%
"""
        )

    prompt = f"""
Ты помощник по кулинарии.

Пользователь указал продукты:
{", ".join(user_ingredients)}

Вот найденные варианты блюд:
{chr(10).join(meals_text_blocks)}

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
        return await hf_chat(prompt, max_tokens=1200)
    except Exception:
        lines = ["🍽 Что можно приготовить", ""]
        for meal in best_meals[:5]:
            lines.append(
                f"• {meal['title']} — совпадение {meal['coverage']}%, "
                f"есть: {', '.join(meal['matched']) if meal['matched'] else 'нет'}"
            )
        return "\n".join(lines)


async def show_main_menu(message: Message, text: str = "Выберите действие:"):
    await message.answer(text, reply_markup=main_menu_reply_keyboard)
    await message.answer("Или выберите действие кнопкой ниже:", reply_markup=kb_main())


async def start_workout_flow_message(message: Message):
    uid = message.from_user.id
    user_mode[uid] = "workout"
    workout_state[uid] = WorkoutState()
    await message.answer("Цель?", reply_markup=kb_w_goal())


async def start_meal_flow_message(message: Message):
    uid = message.from_user.id
    user_mode[uid] = "meal"
    meal_state[uid] = MealState()
    await message.answer("Цель питания?", reply_markup=kb_p_goal())


async def start_recipe_flow_message(message: Message):
    uid = message.from_user.id
    user_mode[uid] = "recipes"
    await message.answer(
        "Введите продукты через запятую.\nПример: курица, рис, яйца, сыр, помидоры",
        reply_markup=kb_back()
    )




@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    reset_user_state(uid)
    await show_main_menu(message, text_start)


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    uid = message.from_user.id
    reset_user_state(uid)
    await show_main_menu(message, "Меню:")


@dp.callback_query(F.data == "m:back")
async def back_menu(call: CallbackQuery):
    uid = call.from_user.id
    reset_user_state(uid)

    await drop_kb(call)
    await call.message.answer("Меню:", reply_markup=main_menu_reply_keyboard)
    await call.message.answer("Или выберите действие кнопкой ниже:", reply_markup=kb_main())
    await call.answer()




@dp.callback_query(F.data == "m:workout")
async def menu_workout(call: CallbackQuery):
    uid = call.from_user.id
    user_mode[uid] = "workout"
    workout_state[uid] = WorkoutState()

    await drop_kb(call)
    await call.message.answer("Цель?", reply_markup=kb_w_goal())
    await call.answer()


@dp.callback_query(F.data == "m:meal")
async def menu_meal(call: CallbackQuery):
    uid = call.from_user.id
    user_mode[uid] = "meal"
    meal_state[uid] = MealState()

    await drop_kb(call)
    await call.message.answer("Цель питания?", reply_markup=kb_p_goal())
    await call.answer()


@dp.callback_query(F.data == "m:recipes")
async def menu_recipes(call: CallbackQuery):
    uid = call.from_user.id
    user_mode[uid] = "recipes"

    await drop_kb(call)
    await call.message.answer(
        "Введите продукты через запятую.\nПример: курица, рис, яйца, сыр, помидоры",
        reply_markup=kb_back()
    )
    await call.answer()




@dp.message(F.text == text_make_training_plan)
async def text_menu_training(message: Message):
    await message.answer(text_training_plan_started)
    await start_workout_flow_message(message)


@dp.message(F.text == text_make_meal_plan)
async def text_menu_meal(message: Message):
    await message.answer(text_meal_plan_started)
    await start_meal_flow_message(message)


@dp.message(F.text == text_find_recipe)
async def text_menu_recipe(message: Message):
    await message.answer(text_find_recipe_started)
    await start_recipe_flow_message(message)




@dp.callback_query(F.data.startswith("w:goal:"))
async def w_goal(call: CallbackQuery):
    uid = call.from_user.id
    if user_mode.get(uid) != "workout":
        await call.answer("Откройте /menu", show_alert=True)
        return

    workout_state.setdefault(uid, WorkoutState()).goal = call.data.split(":")[-1]
    await drop_kb(call)
    await call.message.answer("Уровень?", reply_markup=kb_w_level())
    await call.answer()


@dp.callback_query(F.data.startswith("w:level:"))
async def w_level(call: CallbackQuery):
    uid = call.from_user.id
    if user_mode.get(uid) != "workout":
        await call.answer("Откройте /menu", show_alert=True)
        return

    workout_state.setdefault(uid, WorkoutState()).level = call.data.split(":")[-1]
    await drop_kb(call)
    await call.message.answer("Сколько дней в неделю?", reply_markup=kb_days_1_7("w:days"))
    await call.answer()


@dp.callback_query(F.data.startswith("w:days:"))
async def w_days(call: CallbackQuery):
    uid = call.from_user.id
    if user_mode.get(uid) != "workout":
        await call.answer("Откройте /menu", show_alert=True)
        return

    days = int(call.data.split(":")[-1])
    workout_state.setdefault(uid, WorkoutState()).days = days
    await drop_kb(call)
    await call.message.answer("Инвентарь?", reply_markup=kb_w_inventory())
    await call.answer()


@dp.callback_query(F.data.startswith("w:eq:"))
async def w_eq(call: CallbackQuery):
    uid = call.from_user.id
    if user_mode.get(uid) != "workout":
        await call.answer("Откройте /menu", show_alert=True)
        return

    st = workout_state.setdefault(uid, WorkoutState())
    st.eq = call.data.split(":")[-1]

    goal_map = {
        "strength": "сила",
        "fatloss": "похудение",
        "endurance": "выносливость"
    }
    level_map = {
        "beginner": "новичок",
        "intermediate": "средний"
    }
    eq_map = {
        "home": "дом",
        "gym": "зал"
    }

    await drop_kb(call)
    await call.message.answer("Генерирую план тренировок… ⏳")

    prompt = f"""
Ты спортивный тренер. Составь план тренировок на 7 дней.

Вход:
- цель: {goal_map.get(st.goal, st.goal)}
- уровень: {level_map.get(st.level, st.level)}
- тренировок в неделю: {st.days}
- инвентарь: {eq_map.get(st.eq, st.eq)}

Формат ответа строго:
День 1:
- Разминка: ...
- Упражнения:
  1) ... — подходы x повторы, отдых ...
  2) ...
- Заминка: ...
...
День 7: ...

Правила:
- Ровно {st.days} тренировочных дней, остальные — отдых/лёгкая активность.
- Для "дом": без тренажёров.
- Для "зал": базовые упражнения со штангой/гантелями.
- Без лишних объяснений.
""".strip()

    try:
        text = await hf_chat(prompt, max_tokens=900)
        await call.message.answer(text, reply_markup=kb_back())
    except Exception as e:
        print("HF ERROR:", repr(e))
        await call.message.answer("ИИ временно недоступен. Попробуйте позже.", reply_markup=kb_back())

    reset_user_state(uid)
    await call.answer()




@dp.callback_query(F.data.startswith("p:goal:"))
async def p_goal(call: CallbackQuery):
    uid = call.from_user.id
    if user_mode.get(uid) != "meal":
        await call.answer("Откройте /menu", show_alert=True)
        return

    meal_state.setdefault(uid, MealState()).goal = call.data.split(":")[-1]
    await drop_kb(call)
    await call.message.answer("Сколько тренировок в неделю?", reply_markup=kb_days_1_7("p:days"))
    await call.answer()


@dp.callback_query(F.data.startswith("p:days:"))
async def p_days(call: CallbackQuery):
    uid = call.from_user.id
    if user_mode.get(uid) != "meal":
        await call.answer("Откройте /menu", show_alert=True)
        return

    days = int(call.data.split(":")[-1])
    meal_state.setdefault(uid, MealState()).days = days
    await drop_kb(call)
    await call.message.answer("Есть ограничения?", reply_markup=kb_p_restrictions())
    await call.answer()


@dp.callback_query(F.data.startswith("p:res:"))
async def p_res(call: CallbackQuery):
    uid = call.from_user.id
    if user_mode.get(uid) != "meal":
        await call.answer("Откройте /menu", show_alert=True)
        return

    st = meal_state.setdefault(uid, MealState())
    st.restriction = call.data.split(":")[-1]

    goal_map = {
        "fatloss": "похудение",
        "bulk": "набор массы",
        "maintain": "поддержание"
    }
    res_map = {
        "nodairy": "без молочного",
        "nomeat": "без мяса",
        "nogluten": "без глютена",
        "none": "без ограничений"
    }

    await drop_kb(call)
    await call.message.answer("Генерирую план питания… ⏳")

    prompt = f"""
Составь план питания на 7 дней (завтрак, обед, ужин, 1 перекус).
Данные:
- цель: {goal_map.get(st.goal, st.goal)}
- тренировок в неделю: {st.days}
- ограничения: {res_map.get(st.restriction, st.restriction)}

Формат строго:
День 1:
- Завтрак: ...
- Обед: ...
- Ужин: ...
- Перекус: ...
...
День 7: ...

Правила:
- Простые блюда из обычных продуктов.
- Учитывай цель.
- Без лишних объяснений.
""".strip()

    try:
        text = await hf_chat(prompt, max_tokens=900)
        await call.message.answer(text, reply_markup=kb_back())
    except Exception as e:
        print("HF ERROR:", repr(e))
        await call.message.answer("ИИ временно недоступен. Попробуйте позже.", reply_markup=kb_back())

    reset_user_state(uid)
    await call.answer()




@dp.message(F.text)
async def recipes_text(message: Message):
    uid = message.from_user.id
    if user_mode.get(uid) != "recipes":
        return

    ingredients = parse_ingredients_ru_en(message.text)
    if not ingredients:
        await message.answer(
            "Не понял ингредиенты. Напиши так: курица, рис, яйца, сыр, картошка",
            reply_markup=kb_back()
        )
        return

    await message.answer("Смотрю, что можно приготовить из всего списка… ⏳")

    try:
        result_text = await generate_menu_from_ingredients(ingredients)
        await message.answer(result_text, reply_markup=kb_back())
    except Exception as e:
        print("RECIPES ERROR:", repr(e))
        await message.answer(
            "Не удалось подобрать блюда. Попробуйте позже.",
            reply_markup=kb_back()
        )

    user_mode.pop(uid, None)



async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())