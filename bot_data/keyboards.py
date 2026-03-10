from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


workout_goal_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Сила")],
        [KeyboardButton(text="Похудение")],
        [KeyboardButton(text="Выносливость")],
    ],
    resize_keyboard=True,
)


workout_level_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Новичок"), KeyboardButton(text="Средний")],
    ],
    resize_keyboard=True,
)


days_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3")],
        [KeyboardButton(text="4"), KeyboardButton(text="5"), KeyboardButton(text="6")],
        [KeyboardButton(text="7")],
    ],
    resize_keyboard=True,
)


workout_equipment_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Дом"), KeyboardButton(text="Зал")],
    ],
    resize_keyboard=True,
)


meal_goal_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Похудение")],
        [KeyboardButton(text="Набор массы")],
        [KeyboardButton(text="Поддержание")],
    ],
    resize_keyboard=True,
)


meal_restrictions_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Без молочного"), KeyboardButton(text="Без мяса")],
        [KeyboardButton(text="Без глютена"), KeyboardButton(text="Без ограничений")],
    ],
    resize_keyboard=True,
)