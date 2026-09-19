from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env and loads variables into the environment

client = OpenAI(
    api_key=os.environ.get("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


completion = client.chat.completions.create(
  model="gemini-2.5-pro",
  messages=[
    # {"role": "developer", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of India"}
  ]
)

print(completion.choices[0].message)