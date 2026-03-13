from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import ReplyKeyboardRemove

from bot_data.state import reset_user_state

router = Router()


@router.message(CommandStart())
async def send_welcome_message(message: types.Message):
    reset_user_state(message.from_user.id)

    await message.answer(
        f"🎉 <b>Добро пожаловать, {message.from_user.first_name}!</b>\n\n"
        f"Я помогу тебе с тренировками, питанием, подбором рецептов и свободными вопросами.\n\n"
        f"📌 Что я могу сделать для тебя:\n"
        f"• составить план тренировок\n"
        f"• предложить план питания\n"
        f"• подобрать рецепт по продуктам\n"
        f"• ответить на свободный вопрос через ИИ\n\n"
        f"Напиши <b>/help</b>, чтобы посмотреть все доступные команды.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(Command("help"))
async def send_help_message(message: types.Message):
    await message.answer(
        f"📖 <b>Доступные команды</b>\n\n"
        "🚀 /start — запустить бота\n"
        "❓ /help — открыть это меню\n\n"
        "🏋️ /training_plan\n"
        "    <i>Создать персональный план тренировок</i>\n\n"
        "🍽 /meal_plan\n"
        "    <i>Создать план питания под твою цель</i>\n\n"
        "🥘 /recipe_search\n"
        "    <i>Найти рецепты по тем продуктам, которые у тебя есть</i>\n\n"
        "🤖 /ai вопрос\n"
        "    <i>Задать свободный вопрос нейросети</i>\n\n",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )