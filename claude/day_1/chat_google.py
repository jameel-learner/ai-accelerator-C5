"""
Google Gemini - two ways to make the same call.

1. OpenAI-compatible endpoint - via the generic `openai` SDK.
2. Native `google-genai` SDK  - Google's own client library, with its
                                 own request/response shape.
Docs: https://ai.google.dev/gemini-api/docs/openai
      https://ai.google.dev/gemini-api/docs/quickstart
"""
import os
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

load_dotenv()  # reads .env and loads variables into the environment

question = "What is the capital of India?"


def call_via_openai_compatible() -> str:
    client = OpenAI(
        api_key=os.environ.get("GOOGLE_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    response = client.chat.completions.create(
        model="gemini-3.6-flash",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


def call_via_native_sdk() -> str:
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    # Chat.send_message is Google's recommended entry point (handles
    # automatic function calling correctly); generate_content is the
    # lower-level, stateless call and triggers the AFC warning instead.
    chat = client.chats.create(
        model="gemini-3.6-flash",
        config={"system_instruction": "You are a helpful assistant."},
    )
    response = chat.send_message(question)
    return response.text


if __name__ == "__main__":
    print("=== OpenAI-compatible endpoint ===")
    print(call_via_openai_compatible())
    print()
    print("=== Native google-genai SDK ===")
    print(call_via_native_sdk())
