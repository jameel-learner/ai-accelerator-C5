"""
Gradio Chat App: streaming responses from free OpenRouter models.

Features:
- Text input box + streaming output area (via gr.ChatInterface)
- Connects to OpenRouter using the OpenAI-compatible client
- Dropdown to switch between a few free OpenRouter models
- Switching models starts a brand new conversation thread
"""

import os
import tomllib
from pathlib import Path

import gradio as gr
from openai import OpenAI

# --- Load the OpenRouter API key -------------------------------------------------
# Reuses the key already saved for the Streamlit chatbot demo, falling back to an
# environment variable if that file isn't present.
SECRETS_PATH = Path(__file__).parent / "chatgpt" / ".streamlit" / "secrets.toml"

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key and SECRETS_PATH.exists():
    with open(SECRETS_PATH, "rb") as f:
        api_key = tomllib.load(f).get("OPENROUTER_API_KEY")

if not api_key:
    raise RuntimeError(
        "Missing OPENROUTER_API_KEY. Set it as an environment variable or add it to "
        f"{SECRETS_PATH}"
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    default_headers={
        "HTTP-Referer": "http://localhost:7860",
        "X-Title": "Gradio ChatBot",
    },
)

# --- Available free OpenRouter models --------------------------------------------
MODELS = [
    "openai/gpt-oss-20b",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat-v3.1",
]
DEFAULT_MODEL = MODELS[0]


def clean(text: str) -> str:
    for token in ("<s>", "<|im_start|>", "<|im_end|>", "<|OUT|>"):
        text = text.replace(token, "")
    return text


def respond(message, history, model):
    """Stream a reply from OpenRouter for the given model + history."""
    messages = []       #{"role": "system", "content": "You are Banking assitance and nothing else"}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            extra_headers={
                "HTTP-Referer": "http://localhost:7860",
                "X-Title": "Gradio ChatBot",
            },
            extra_body={"provider": {"data_collection": "deny"}},
        )
    except Exception as e:
        yield f"Error: {e}"
        return

    partial = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            partial += clean(delta)
            yield partial


with gr.Blocks(title="Gradio ChatBot") as demo:
    gr.Markdown("# 🤖 Gradio ChatBot (OpenRouter)")

    model_dropdown = gr.Dropdown(
        choices=MODELS,
        value=DEFAULT_MODEL,
        label="Model",
        info="Switching models starts a new conversation",
    )

    chat = gr.ChatInterface(
        fn=respond,
        additional_inputs=[model_dropdown],
    )

    def new_thread(_model):
        return []

    # Changing the model clears the chat history to start a fresh thread.
    model_dropdown.change(fn=new_thread, inputs=model_dropdown, outputs=chat.chatbot)


if __name__ == "__main__":
    demo.launch()
