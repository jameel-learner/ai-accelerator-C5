"""
OpenAI - two ways to make the same call.

1. Chat Completions API   - the original, still-supported endpoint.
2. Responses API          - OpenAI's newer native interface (recommended
                            going forward; simpler stateful/streaming story).
Docs: https://platform.openai.com/docs/api-reference/chat
      https://platform.openai.com/docs/api-reference/responses
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env and loads variables into the environment

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

question = "What is the capital of India?"


def call_via_chat_completions() -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


def call_via_responses_api() -> str:
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions="You are a helpful assistant.",
        input=question,
    )
    return response.output_text


if __name__ == "__main__":
    print("=== Chat Completions API ===")
    print(call_via_chat_completions())
    print()
    print("=== Responses API (native) ===")
    print(call_via_responses_api())
