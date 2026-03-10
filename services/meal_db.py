import httpx


class MealDB:
    BASE = "https://www.themealdb.com/api/json/v1/1"

    async def by_ingredient(self, ingredient: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.BASE}/filter.php", params={"i": ingredient})
            response.raise_for_status()
            return response.json().get("meals") or []

    async def details(self, meal_id: str) -> dict | None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.BASE}/lookup.php", params={"i": meal_id})
            response.raise_for_status()
            meals = response.json().get("meals") or []
            return meals[0] if meals else None


meal_db = MealDB()