import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env and loads variables into the environment

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

response = client.chat.completions.create(
    model="nvidia/nemotron-3-ultra-550b-a55b:free",
    # model="openai/gpt-4o-mini",
    messages=[
        # {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "what is the capital of france?"},
        {"role": "assistant", "content": "'The capital of France is **Paris**."},
        {"role": "user", "content": "tell me 10 line about it"},
    ]
)

print(response.choices[0].message)
# print(response.choices[0].message.content)