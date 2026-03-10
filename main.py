import os
import asyncio
import logging

from openai import OpenAI
from dotenv import load_dotenv
from handlers import start, training_plan, meal_plan, recipe_search

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand


load_dotenv(override=True)
hf_client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=os.getenv("HF_TOKEN"))
bot = Bot(os.getenv("BOT_TOKEN"))
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(training_plan.router)
dp.include_router(meal_plan.router)
dp.include_router(recipe_search.router)

async def main():
    commands = [
        BotCommand(command="start", description="Запустить бота и открыть главное меню"),
        BotCommand(command="help", description="Показать список команд и подсказки"),
        BotCommand(command="training_plan", description="Составить план тренировок"),
        BotCommand(command="meal_plan", description="Составить план питания"),
        BotCommand(command="recipe_search", description="Подобрать рецепт по продуктам")
    ]
    await bot.set_my_commands(commands)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())