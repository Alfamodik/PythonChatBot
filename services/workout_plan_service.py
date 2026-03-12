from bot_data.state import UserProfile, WorkoutState
from services.hf_client import hf_chat


def build_workout_prompt(profile: UserProfile, workout: WorkoutState) -> str:
    sex_name_map = {
        "male": "мужчина",
        "female": "женщина",
    }
    goal_name_map = {
        "strength": "сила",
        "fatloss": "похудение",
        "endurance": "выносливость",
        "muscle_gain": "набор мышц",
    }
    level_name_map = {
        "beginner": "новичок",
        "intermediate": "средний",
    }
    equipment_name_map = {
        "home": "дом",
        "gym": "зал",
    }
    priority_name_map = {
        "all_body": "всё тело",
        "legs_and_glutes": "ноги и ягодицы",
        "back": "спина",
        "chest_and_arms": "грудь и руки",
        "shoulders": "плечи",
        "abs": "пресс",
    }

    body_fat_text = (
        f"{profile.body_fat_percent}%"
        if profile.body_fat_percent is not None
        else "неизвестен"
    )

    return f"""
Ты опытный фитнес-тренер. Составь качественный персональный недельный план тренировок на 7 дней.

Данные клиента:
- пол: {sex_name_map.get(profile.sex, profile.sex) if profile.sex else "неизвестно"}
- возраст: {profile.age if profile.age is not None else "неизвестно"}
- рост: {f"{profile.height_in_centimeters} см" if profile.height_in_centimeters is not None else "неизвестно"}
- вес: {f"{profile.weight_in_kilograms} кг" if profile.weight_in_kilograms is not None else "неизвестно"}
- процент жира: {body_fat_text}
- цель: {goal_name_map.get(workout.goal, workout.goal) if workout.goal else "неизвестно"}
- уровень: {level_name_map.get(workout.level, workout.level)}
- тренировок в неделю: {workout.days_per_week}
- инвентарь: {equipment_name_map.get(workout.equipment, workout.equipment)}
- приоритет: {priority_name_map.get(workout.priority_muscle_groups, workout.priority_muscle_groups)}

Правила:
1. Составь недельный план ровно на 7 дней.
2. Тренировочных дней должно быть ровно {workout.days_per_week}.
3. Остальные дни обозначь как отдых, ходьба, мобильность или лёгкая активность.
4. Для каждого тренировочного дня укажи конкретные упражнения.
5. Для каждого упражнения обязательно укажи подходы, повторения и отдых.
6. Не используй markdown-таблицы.
7. Оформляй весь ответ только списками и обычным текстом.
8. Используй только понятные и общеизвестные названия упражнений.
9. Если пользователь новичок, не давай тяжёлые технические упражнения.
10. Пиши только на русском.
11. Без воды.

Формат ответа строго:

День 1 — тренировка или отдых
- Цель дня: ...
- Разминка: ...
- Упражнения:
  1) Название — 3 подхода по 12 повторений, отдых 60 секунд
  2) Название — 3 подхода по 10 повторений, отдых 75 секунд
- Заминка: ...

День 2 — отдых
- Рекомендация: ...

...
День 7 — ...

В конце отдельно:
- Прогрессия на 4 недели
- Когда снизить нагрузку
- Чем заменить упражнения при дискомфорте
""".strip()


async def generate_workout_plan(profile: UserProfile, workout: WorkoutState) -> str:
    prompt = build_workout_prompt(profile, workout)
    return await hf_chat(prompt, max_tokens=4000)