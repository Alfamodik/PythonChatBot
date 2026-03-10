from dataclasses import dataclass


user_mode: dict[int, str] = {}


@dataclass
class WorkoutState:
    goal: str | None = None
    level: str | None = None
    days_per_week: int | None = None
    equipment: str | None = None


@dataclass
class MealState:
    goal: str | None = None
    trainings_per_week: int | None = None
    restriction: str | None = None


workout_state: dict[int, WorkoutState] = {}
meal_state: dict[int, MealState] = {}


def reset_user_state(user_id: int):
    user_mode.pop(user_id, None)
    workout_state.pop(user_id, None)
    meal_state.pop(user_id, None)