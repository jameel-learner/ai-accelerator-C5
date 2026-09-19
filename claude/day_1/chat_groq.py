"""
Groq - two ways to make the same call.

1. OpenAI-compatible endpoint - via the generic `openai` SDK.
2. Native `groq` SDK          - Groq's own client library.
Docs: https://console.groq.com/docs/openai
      https://console.groq.com/docs/quickstart
"""
import os
from dotenv import load_dotenv
from openai import OpenAI
from groq import Groq

load_dotenv()  # reads .env and loads variables into the environment

question = "What is the capital of India?"


def call_via_openai_compatible() -> str:
    client = OpenAI(
        api_key=os.environ.get("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    response = client.chat.completions.create(
        model="groq/compound-mini",    #"llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


def call_via_native_sdk() -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="groq/compound-mini",     # "llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print("=== OpenAI-compatible endpoint ===")
    print(call_via_openai_compatible())
    print()
    print("=== Native Groq SDK ===")
    print(call_via_native_sdk())
