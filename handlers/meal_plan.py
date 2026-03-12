from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from bot_data.keyboards import (
    meal_goal_reply_keyboard,
    meal_restrictions_reply_keyboard,
    workout_body_fat_reply_keyboard,
    workout_sex_reply_keyboard,
)
from bot_data.state import (
    MealState,
    UserProfile,
    meal_state,
    reset_user_state,
    user_mode,
    user_profile_state,
)
from services.meal_plan_service import MealTargets, generate_meal_plan

router = Router()


def is_meal_mode(message: Message, mode: str) -> bool:
    return user_mode.get(message.from_user.id) == mode


async def send_long_message(message: Message, text: str, max_length: int = 3500):
    text_parts: list[str] = []

    while len(text) > max_length:
        split_index = text.rfind("\n", 0, max_length)
        if split_index == -1:
            split_index = max_length

        text_parts.append(text[:split_index].strip())
        text = text[split_index:].strip()

    if text:
        text_parts.append(text)

    print("TEXT PARTS COUNT:", len(text_parts))

    for index, text_part in enumerate(text_parts, start=1):
        print(f"SEND PART {index} LENGTH:", len(text_part))
        await message.answer(text_part, reply_markup=ReplyKeyboardRemove())


def build_targets_summary(targets: MealTargets) -> str:
    return (
        "Расчёт готов:\n"
        f"- Базовый обмен: {targets.bmr_calories} ккал\n"
        f"- Поддержание: {targets.maintenance_calories} ккал\n"
        f"- Целевые калории: {targets.target_calories} ккал\n"
        f"- Белок: {targets.protein_grams} г\n"
        f"- Жиры: {targets.fat_grams} г\n"
        f"- Углеводы: {targets.carbohydrate_grams} г"
    )


async def start_meal_flow(message: Message):
    user_id = message.from_user.id
    user_mode[user_id] = "meal_sex"
    meal_state[user_id] = MealState()

    await message.answer("Укажите пол:", reply_markup=workout_sex_reply_keyboard)


@router.message(Command("meal_plan"))
async def command_meal_plan(message: Message):
    await start_meal_flow(message)


@router.message(lambda message: is_meal_mode(message, "meal_sex") and message.text in {"Мужчина", "Женщина"})
async def select_meal_sex(message: Message):
    user_id = message.from_user.id

    sex_map = {
        "Мужчина": "male",
        "Женщина": "female",
    }

    meal_state.setdefault(user_id, MealState()).sex = sex_map[message.text]
    user_mode[user_id] = "meal_age"

    await message.answer("Введите возраст числом. Например: 20", reply_markup=ReplyKeyboardRemove())


@router.message(lambda message: is_meal_mode(message, "meal_age"))
async def input_meal_age(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if not text.isdigit():
        await message.answer("Введите возраст числом. Например: 20")
        return

    age = int(text)
    if age < 12 or age > 80:
        await message.answer("Введите возраст в пределах от 12 до 80.")
        return

    meal_state.setdefault(user_id, MealState()).age = age
    user_mode[user_id] = "meal_height"

    await message.answer("Введите рост в сантиметрах. Например: 180")


@router.message(lambda message: is_meal_mode(message, "meal_height"))
async def input_meal_height(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if not text.isdigit():
        await message.answer("Введите рост числом. Например: 180")
        return

    height_in_centimeters = int(text)
    if height_in_centimeters < 120 or height_in_centimeters > 230:
        await message.answer("Введите рост в пределах от 120 до 230 см.")
        return

    meal_state.setdefault(user_id, MealState()).height_in_centimeters = height_in_centimeters
    user_mode[user_id] = "meal_weight"

    await message.answer("Введите вес в килограммах. Например: 80")


@router.message(lambda message: is_meal_mode(message, "meal_weight"))
async def input_meal_weight(message: Message):
    user_id = message.from_user.id
    text = message.text.strip().replace(",", ".")

    try:
        weight_in_kilograms = float(text)
    except ValueError:
        await message.answer("Введите вес числом. Например: 80 или 72.5")
        return

    if weight_in_kilograms < 30 or weight_in_kilograms > 300:
        await message.answer("Введите вес в разумных пределах.")
        return

    meal_state.setdefault(user_id, MealState()).weight_in_kilograms = weight_in_kilograms
    user_mode[user_id] = "meal_body_fat"

    await message.answer(
        "Введите примерный процент жира числом. Например: 18\nЕсли не знаете, нажмите кнопку.",
        reply_markup=workout_body_fat_reply_keyboard,
    )


@router.message(lambda message: is_meal_mode(message, "meal_body_fat") and message.text == "Не знаю")
async def skip_meal_body_fat(message: Message):
    user_id = message.from_user.id

    meal_state.setdefault(user_id, MealState()).body_fat_percent = None
    user_mode[user_id] = "meal_goal"

    await message.answer("Выберите цель питания:", reply_markup=meal_goal_reply_keyboard)


@router.message(lambda message: is_meal_mode(message, "meal_body_fat"))
async def input_meal_body_fat(message: Message):
    user_id = message.from_user.id
    text = message.text.strip().replace(",", ".")

    try:
        body_fat_percent = float(text)
    except ValueError:
        await message.answer("Введите процент жира числом. Например: 18 или 20,5")
        return

    if body_fat_percent < 3 or body_fat_percent > 60:
        await message.answer("Введите процент жира в разумных пределах.")
        return

    meal_state.setdefault(user_id, MealState()).body_fat_percent = body_fat_percent
    user_mode[user_id] = "meal_goal"

    await message.answer("Выберите цель питания:", reply_markup=meal_goal_reply_keyboard)


@router.message(lambda message: is_meal_mode(message, "meal_goal") and message.text in {"Похудение", "Набор массы", "Поддержание"})
async def select_meal_goal(message: Message):
    user_id = message.from_user.id

    goal_map = {
        "Похудение": "fatloss",
        "Набор массы": "bulk",
        "Поддержание": "maintain",
    }

    meal_state.setdefault(user_id, MealState()).goal = goal_map[message.text]
    user_mode[user_id] = "meal_restrictions"

    await message.answer("Есть ограничения?", reply_markup=meal_restrictions_reply_keyboard)


@router.message(lambda message: is_meal_mode(message, "meal_restrictions") and message.text in {"Без молочного", "Без мяса", "Без глютена", "Без ограничений"})
async def select_meal_restrictions(message: Message):
    user_id = message.from_user.id

    restriction_map = {
        "Без молочного": "nodairy",
        "Без мяса": "nomeat",
        "Без глютена": "nogluten",
        "Без ограничений": "none",
    }

    state = meal_state.setdefault(user_id, MealState())
    state.restriction = restriction_map[message.text]

    user_profile_state[user_id] = UserProfile(
        sex=state.sex,
        age=state.age,
        height_in_centimeters=state.height_in_centimeters,
        weight_in_kilograms=state.weight_in_kilograms,
        body_fat_percent=state.body_fat_percent,
    )

    await message.answer("Генерирую план питания… ⏳", reply_markup=ReplyKeyboardRemove())

    try:
        targets, response_text = await generate_meal_plan(state)

        print("MEAL RESPONSE LENGTH:", len(response_text))
        print("MEAL RESPONSE PREVIEW:", repr(response_text[:500]))

        await message.answer(build_targets_summary(targets), reply_markup=ReplyKeyboardRemove())

        if not response_text.strip():
            await message.answer(
                "Не удалось получить текст плана питания. Попробуйте ещё раз.",
                reply_markup=ReplyKeyboardRemove(),
            )
            reset_user_state(user_id)
            return

        await send_long_message(message, response_text)
    except Exception as exception:
        print("HF ERROR:", repr(exception))
        await message.answer(
            "ИИ временно недоступен. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove(),
        )

    reset_user_state(user_id)