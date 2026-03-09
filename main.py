#hf
from dotenv import load_dotenv
import os
from openai import OpenAI

#tg
from aiogram import F
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
import asyncio


load_dotenv(override=True)
bot_token = os.getenv("BOT_TOKEN")
hf_token = os.getenv("HF_TOKEN")

hf_base_url = "https://router.huggingface.co/v1"
hf_chat_model = "katanemo/Arch-Router-1.5B:hf-inference"

hf_client = OpenAI(base_url=hf_base_url, api_key=hf_token)

bot = Bot(bot_token)
dispatcher = Dispatcher()

prompt = """
Ты спортивный тренер.
Составь план тренировок на 7 дней.

Цель: набор мышечной массы
Уровень: новичок
Тренировок в неделю: 3
Инвентарь: зал

Формат ответа:
День 1:
- ...
День 2:
- ...
"""

#response = hf_client.chat.completions.create(model=hf_chat_model, messages=[{"role": "user", "content": prompt}])
#print(response.choices[0].message.content)

text_start = "Привет, чем могу помочь?"

text_make_training_plan = "Составить план тренировок"
text_training_plan_started = "Сейчас составим план тренировок"

text_make_meal_plan = "Составиль план питания"
text_meal_plan_started = "Сейчас составим план питания"

text_find_recipe = "Найти рецепт"
text_find_recipe_started = "Сейчас поищем"

text_input_placeholder = "Выберите действие"

main_menu_keyboard = ReplyKeyboardMarkup(
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
    input_field_placeholder=text_input_placeholder
)


@dispatcher.message(Command("start"))
async def start(message: Message):
    await message.answer(text_start, reply_markup=main_menu_keyboard)


@dispatcher.message(F.text == text_make_training_plan)
async def workout(message: Message):
    await message.reply(text_training_plan_started)


@dispatcher.message(F.text == text_make_meal_plan)
async def workout(message: Message):
    await message.reply(text_meal_plan_started)


@dispatcher.message(F.text == text_find_recipe)
async def workout(message: Message):
    await message.reply(text_find_recipe_started)


async def main():
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
