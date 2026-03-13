import asyncio
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

hf_token = (os.getenv("HF_TOKEN") or "").strip()

if not hf_token:
    raise ValueError("HF_TOKEN не найден")

hf_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=hf_token,
)

hf_chat_model = "openai/gpt-oss-20b"
hf_chat_model_meal = "katanemo/Arch-Router-1.5B:hf-inference"


async def hf_chat(prompt: str) -> str:
    def call() -> str:
        response = hf_client.chat.completions.create(
            model=hf_chat_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        return (response.choices[0].message.content or "").strip()

    return await asyncio.to_thread(call)

async def hf_chat_meal(prompt: str) -> str:
    def call() -> str:
        response = hf_client.chat.completions.create(
            model=hf_chat_model_meal,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        return (response.choices[0].message.content or "").strip()

    return await asyncio.to_thread(call)