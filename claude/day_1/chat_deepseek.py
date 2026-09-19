"""
DeepSeek - two ways to make the same call.

1. OpenAI-compatible endpoint - via the generic `openai` SDK.
2. Native REST API            - DeepSeek does not publish its own Python
                                 SDK; its documented "native" integration
                                 path is raw HTTP against its REST API, so
                                 that's shown here via `requests` instead
                                 of depending on the `openai` package.
Docs: https://api-docs.deepseek.com/
"""
import os
from dotenv import load_dotenv
import requests
from openai import OpenAI

load_dotenv()  # reads .env and loads variables into the environment

question = "What is the capital of India?"


def call_via_openai_compatible() -> str:
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


def call_via_native_rest_api() -> str:
    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ],
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    print("=== OpenAI-compatible endpoint (openai SDK) ===")
    print(call_via_openai_compatible())
    print()
    print("=== Native REST API (raw HTTP, no SDK) ===")
    print(call_via_native_rest_api())
