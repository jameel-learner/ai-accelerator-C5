"""
Anthropic (Claude) - Messages API
Anthropic does not expose an OpenAI-style "chat.completions" endpoint -
it uses its own Messages API via the native `anthropic` SDK instead of
an OpenAI-compatible shim. This is the one provider in this folder that
is intentionally NOT called through the `openai` client.
Docs: https://docs.claude.com/en/api/messages
"""
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()  # reads .env and loads variables into the environment

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=1024,
    system="You are a helpful assistant.",
    messages=[
        {"role": "user", "content": "What is the capital of India?"},
    ],
)

for block in response.content:
    if block.type == "text":
        print(block.text)
