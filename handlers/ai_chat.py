from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove

from services.hf_client import hf_chat

router = Router()


async def send_long_message(message: types.Message, text: str, max_length: int = 3500):
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


@router.message(Command("ai"))
async def ai_command(message: types.Message):
    print("AI COMMAND HANDLER WORKED", message.text)
    message_text = (message.text or "").strip()
    prompt = message_text[3:].strip()

    if not prompt:
        await message.answer(
            "Напишите вопрос после команды.\nПример:\n/ai что такое тренировки?",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await message.answer("Думаю…", reply_markup=ReplyKeyboardRemove())

    system_prompt = """
Ты полезный ИИ-помощник.
Отвечай только на русском.
Пиши понятно, кратко и по делу.
""".strip()

    full_prompt = f"""
{system_prompt}

Вопрос пользователя:
{prompt}
""".strip()

    response_text = await hf_chat(full_prompt)

    if not response_text.strip():
        await message.answer("Не удалось получить ответ.")
        return

    await send_long_message(message, response_text)