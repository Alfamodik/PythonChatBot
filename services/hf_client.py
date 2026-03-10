import asyncio
import os

from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

HF_CHAT_MODEL = "katanemo/Arch-Router-1.5B:hf-inference"
hf_client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=os.getenv("HF_TOKEN"))


async def hf_chat(prompt: str, max_tokens: int = 800) -> str:
    def call() -> str:
        response = hf_client.chat.completions.create(
            model=HF_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    return await asyncio.to_thread(call)