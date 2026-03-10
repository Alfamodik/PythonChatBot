from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from bot_data.keyboards import (
    days_reply_keyboard,
    workout_equipment_reply_keyboard,
    workout_goal_reply_keyboard,
    workout_level_reply_keyboard,
)
from bot_data.state import WorkoutState, reset_user_state, user_mode, workout_state
from services.hf_client import hf_chat

router = Router()


async def start_workout_flow(message: Message):
    user_id = message.from_user.id
    user_mode[user_id] = "workout_goal"
    workout_state[user_id] = WorkoutState()

    await message.answer("Выберите цель:", reply_markup=workout_goal_reply_keyboard)


@router.message(Command("training_plan"))
async def command_training_plan(message: Message):
    await start_workout_flow(message)


@router.message(F.text.in_({"Сила", "Похудение", "Выносливость"}))
async def select_workout_goal(message: Message):
    user_id = message.from_user.id

    if user_mode.get(user_id) != "workout_goal":
        return

    goal_map = {
        "Сила": "strength",
        "Похудение": "fatloss",
        "Выносливость": "endurance",
    }

    workout_state.setdefault(user_id, WorkoutState()).goal = goal_map[message.text]
    user_mode[user_id] = "workout_level"

    await message.answer("Выберите уровень:", reply_markup=workout_level_reply_keyboard)


@router.message(F.text.in_({"Новичок", "Средний"}))
async def select_workout_level(message: Message):
    user_id = message.from_user.id

    if user_mode.get(user_id) != "workout_level":
        return

    level_map = {
        "Новичок": "beginner",
        "Средний": "intermediate",
    }

    workout_state.setdefault(user_id, WorkoutState()).level = level_map[message.text]
    user_mode[user_id] = "workout_days"

    await message.answer("Сколько дней в неделю?", reply_markup=days_reply_keyboard)


@router.message(F.text.in_({"1", "2", "3", "4", "5", "6", "7"}))
async def select_workout_days(message: Message):
    user_id = message.from_user.id

    if user_mode.get(user_id) != "workout_days":
        return

    workout_state.setdefault(user_id, WorkoutState()).days_per_week = int(message.text)
    user_mode[user_id] = "workout_equipment"

    await message.answer("Где будете тренироваться?", reply_markup=workout_equipment_reply_keyboard)


@router.message(F.text.in_({"Дом", "Зал"}))
async def select_workout_equipment(message: Message):
    user_id = message.from_user.id

    if user_mode.get(user_id) != "workout_equipment":
        return

    equipment_map = {
        "Дом": "home",
        "Зал": "gym",
    }

    state = workout_state.setdefault(user_id, WorkoutState())
    state.equipment = equipment_map[message.text]

    goal_name_map = {
        "strength": "сила",
        "fatloss": "похудение",
        "endurance": "выносливость",
    }
    level_name_map = {
        "beginner": "новичок",
        "intermediate": "средний",
    }
    equipment_name_map = {
        "home": "дом",
        "gym": "зал",
    }

    await message.answer("Генерирую план тренировок… ⏳", reply_markup=ReplyKeyboardRemove())

    prompt = f"""
Ты спортивный тренер. Составь план тренировок на 7 дней.

Вход:
- цель: {goal_name_map.get(state.goal, state.goal)}
- уровень: {level_name_map.get(state.level, state.level)}
- тренировок в неделю: {state.days_per_week}
- инвентарь: {equipment_name_map.get(state.equipment, state.equipment)}

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
- Ровно {state.days_per_week} тренировочных дней, остальные — отдых или лёгкая активность.
- Для дома: без тренажёров.
- Для зала: базовые упражнения со штангой и гантелями.
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