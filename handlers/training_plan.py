from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from bot_data.keyboards import (
    days_reply_keyboard,
    workout_equipment_reply_keyboard,
    workout_level_reply_keyboard,
    workout_priority_reply_keyboard,
)
from bot_data.state import (
    UserProfile,
    WorkoutState,
    reset_user_state,
    user_mode,
    user_profile_state,
    workout_state,
)
from services.workout_plan_service import generate_workout_plan

router = Router()


def is_workout_mode(message: Message, mode: str) -> bool:
    return user_mode.get(message.from_user.id) == mode


async def send_long_message(message: Message, text: str, max_length: int = 4000):
    text_parts: list[str] = []

    while len(text) > max_length:
        split_index = text.rfind("\n", 0, max_length)
        if split_index == -1:
            split_index = max_length

        text_parts.append(text[:split_index].strip())
        text = text[split_index:].strip()

    if text:
        text_parts.append(text)

    for text_part in text_parts:
        await message.answer(text_part, reply_markup=ReplyKeyboardRemove())


async def start_workout_flow(message: Message):
    user_id = message.from_user.id
    user_mode[user_id] = "workout_level"
    workout_state[user_id] = WorkoutState()

    await message.answer("Выберите уровень:", reply_markup=workout_level_reply_keyboard)


@router.message(Command("training_plan"))
async def command_training_plan(message: Message):
    await start_workout_flow(message)


@router.message(lambda message: is_workout_mode(message, "workout_level") and message.text in {"Новичок", "Средний"})
async def select_workout_level(message: Message):
    user_id = message.from_user.id

    level_map = {
        "Новичок": "beginner",
        "Средний": "intermediate",
    }

    workout_state.setdefault(user_id, WorkoutState()).level = level_map[message.text]
    user_mode[user_id] = "workout_days"

    await message.answer("Сколько тренировок в неделю?", reply_markup=days_reply_keyboard)


@router.message(lambda message: is_workout_mode(message, "workout_days") and message.text in {"1", "2", "3", "4", "5", "6", "7"})
async def select_workout_days(message: Message):
    user_id = message.from_user.id

    workout_state.setdefault(user_id, WorkoutState()).days_per_week = int(message.text)
    user_mode[user_id] = "workout_equipment"

    await message.answer("Где будете тренироваться?", reply_markup=workout_equipment_reply_keyboard)


@router.message(lambda message: is_workout_mode(message, "workout_equipment") and message.text in {"Дом", "Зал"})
async def select_workout_equipment(message: Message):
    user_id = message.from_user.id

    equipment_map = {
        "Дом": "home",
        "Зал": "gym",
    }

    workout_state.setdefault(user_id, WorkoutState()).equipment = equipment_map[message.text]
    user_mode[user_id] = "workout_priority"

    await message.answer("Что хотите сделать приоритетом?", reply_markup=workout_priority_reply_keyboard)


@router.message(
    lambda message: is_workout_mode(message, "workout_priority")
    and message.text in {"Все тело", "Ноги и ягодицы", "Спина", "Грудь и руки", "Плечи", "Пресс"}
)
async def select_workout_priority(message: Message):
    user_id = message.from_user.id

    priority_map = {
        "Все тело": "all_body",
        "Ноги и ягодицы": "legs_and_glutes",
        "Спина": "back",
        "Грудь и руки": "chest_and_arms",
        "Плечи": "shoulders",
        "Пресс": "abs",
    }

    workout = workout_state.setdefault(user_id, WorkoutState())
    workout.priority_muscle_groups = priority_map[message.text]

    profile = user_profile_state.get(user_id)
    if profile is None:
        profile = UserProfile()
        user_profile_state[user_id] = profile

    await message.answer("Генерирую персональный план тренировок… ⏳", reply_markup=ReplyKeyboardRemove())

    try:
        response_text = await generate_workout_plan(profile, workout)
        await message.answer("План готов.", reply_markup=ReplyKeyboardRemove())
        await send_long_message(message, response_text)
    except Exception as exception:
        print("HF ERROR:", repr(exception))
        await message.answer(
            "ИИ временно недоступен. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove(),
        )

    reset_user_state(user_id)