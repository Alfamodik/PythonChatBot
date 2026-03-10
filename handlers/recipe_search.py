from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from bot_data.recipe_utils import generate_menu_from_ingredients, parse_ingredients_ru_en
from bot_data.state import reset_user_state, user_mode

router = Router()


async def start_recipe_flow(message: Message):
    user_id = message.from_user.id
    user_mode[user_id] = "recipes_input"

    await message.answer(
        "Введите продукты через запятую.\nПример: курица, рис, яйца, сыр, помидоры",
    )


@router.message(Command("recipe_search"))
async def command_recipe_search(message: Message):
    await start_recipe_flow(message)


@router.message(F.text)
async def process_recipe_text(message: Message):
    user_id = message.from_user.id

    if user_mode.get(user_id) != "recipes_input":
        return

    ingredients = parse_ingredients_ru_en(message.text)

    if not ingredients:
        await message.answer(
            "Не понял ингредиенты. Напиши так: курица, рис, яйца, сыр, картошка",
        )
        return

    await message.answer("Смотрю, что можно приготовить из всего списка… ⏳", reply_markup=ReplyKeyboardRemove())

    try:
        result_text = await generate_menu_from_ingredients(ingredients)
        await message.answer(result_text, reply_markup=ReplyKeyboardRemove())
    except Exception as exception:
        print("RECIPES ERROR:", repr(exception))
        await message.answer(
            "Не удалось подобрать блюда. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove(),
        )

    reset_user_state(user_id)