from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from bot_data.keyboards import (
    days_reply_keyboard,
    meal_goal_reply_keyboard,
    meal_restrictions_reply_keyboard,
)
from bot_data.state import MealState, meal_state, reset_user_state, user_mode
from services.hf_client import hf_chat

router = Router()


async def start_meal_flow(message: Message):
    user_id = message.from_user.id
    user_mode[user_id] = "meal_goal"
    meal_state[user_id] = MealState()

    await message.answer("Выберите цель питания:", reply_markup=meal_goal_reply_keyboard)


@router.message(Command("meal_plan"))
async def command_meal_plan(message: Message):
    await start_meal_flow(message)


@router.message(F.text.in_({"Похудение", "Набор массы", "Поддержание"}))
async def select_meal_goal(message: Message):
    user_id = message.from_user.id

    if user_mode.get(user_id) != "meal_goal":
        return

    goal_map = {
        "Похудение": "fatloss",
        "Набор массы": "bulk",
        "Поддержание": "maintain",
    }

    meal_state.setdefault(user_id, MealState()).goal = goal_map[message.text]
    user_mode[user_id] = "meal_days"

    await message.answer("Сколько тренировок в неделю?", reply_markup=days_reply_keyboard)


@router.message(F.text.in_({"1", "2", "3", "4", "5", "6", "7"}))
async def select_meal_days(message: Message):
    user_id = message.from_user.id

    if user_mode.get(user_id) != "meal_days":
        return

    meal_state.setdefault(user_id, MealState()).trainings_per_week = int(message.text)
    user_mode[user_id] = "meal_restrictions"

    await message.answer("Есть ограничения?", reply_markup=meal_restrictions_reply_keyboard)


@router.message(F.text.in_({"Без молочного", "Без мяса", "Без глютена", "Без ограничений"}))
async def select_meal_restrictions(message: Message):
    user_id = message.from_user.id

    if user_mode.get(user_id) != "meal_restrictions":
        return

    restriction_map = {
        "Без молочного": "nodairy",
        "Без мяса": "nomeat",
        "Без глютена": "nogluten",
        "Без ограничений": "none",
    }

    state = meal_state.setdefault(user_id, MealState())
    state.restriction = restriction_map[message.text]

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

    await message.answer("Генерирую план питания… ⏳", reply_markup=ReplyKeyboardRemove())

    prompt = f"""
Составь план питания на 7 дней.
Для каждого дня укажи: завтрак, обед, ужин и 1 перекус.

Данные:
- цель: {goal_name_map.get(state.goal, state.goal)}
- тренировок в неделю: {state.trainings_per_week}
- ограничения: {restriction_name_map.get(state.restriction, state.restriction)}

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
- Учитывай цель пользователя.
- Без лишних объяснений.
""".strip()

    try:
        response_text = await hf_chat(prompt, max_tokens=900)
        await message.answer(response_text, reply_markup=ReplyKeyboardRemove())
    except Exception as exception:
        print("HF ERROR:", repr(exception))
        await message.answer(
            "ИИ временно недоступен. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove(),
        )

    reset_user_state(user_id)