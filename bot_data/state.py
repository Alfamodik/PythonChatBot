from dataclasses import dataclass


user_mode: dict[int, str] = {}


@dataclass
class UserProfile:
    sex: str | None = None
    age: int | None = None
    height_in_centimeters: int | None = None
    weight_in_kilograms: float | None = None
    body_fat_percent: float | None = None


@dataclass
class WorkoutState:
    goal: str | None = None
    level: str | None = None
    days_per_week: int | None = None
    equipment: str | None = None
    priority_muscle_groups: str | None = None


@dataclass
class MealState:
    sex: str | None = None
    age: int | None = None
    height_in_centimeters: int | None = None
    weight_in_kilograms: float | None = None
    body_fat_percent: float | None = None
    goal: str | None = None
    restriction: str | None = None


user_profile_state: dict[int, UserProfile] = {}
workout_state: dict[int, WorkoutState] = {}
meal_state: dict[int, MealState] = {}


def reset_user_state(user_id: int):
    user_mode.pop(user_id, None)
    workout_state.pop(user_id, None)
    meal_state.pop(user_id, None)