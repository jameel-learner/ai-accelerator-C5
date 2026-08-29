"""
Gradio Chat App: streaming responses from free OpenRouter models.

Features:
- Text input box + streaming output area (via gr.ChatInterface)
- Connects to OpenRouter using the OpenAI-compatible client
- Dropdown to switch between a few free OpenRouter models
- Switching models starts a brand new conversation thread
"""

import os

import spaces
import gradio as gr
from openai import OpenAI


# --- ZeroGPU startup probe -------------------------------------------------
# ZeroGPU kills the container unless it finds a @spaces.GPU function at import
# time. This app never touches a GPU -- all inference happens remotely on
# OpenRouter's servers -- so this function exists purely to satisfy that check.
# It is never called, so it consumes no ZeroGPU quota.
# If you switch the Space to CPU basic hardware, delete this block and the
# `import spaces` line above.
@spaces.GPU(duration=1)
def _zerogpu_probe():
    return None


# --- Load the OpenRouter API key -------------------------------------------
# On Spaces this comes from Settings -> Variables and secrets -> New secret.
# Locally, python-dotenv or a plain shell export both work.
api_key = os.environ.get("OPENROUTER_API_KEY")

if not api_key:
    raise RuntimeError(
        "Missing OPENROUTER_API_KEY. On Hugging Face Spaces, add it under "
        "Settings -> Variables and secrets. Locally, export it or put it in .env"
    )

# Used by OpenRouter for attribution on their rankings page. Point this at the
# real Space URL rather than localhost once deployed.
APP_URL = os.environ.get("SPACE_HOST", "http://localhost:7860")
APP_TITLE = "Gradio ChatBot"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    default_headers={
        "HTTP-Referer": APP_URL,
        "X-Title": APP_TITLE,
    },
)


# --- Available free OpenRouter models --------------------------------------
MODELS = [
    "openai/gpt-oss-20b",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat-v3.1",
]
DEFAULT_MODEL = MODELS[0]


def clean(text: str) -> str:
    """Strip chat-template control tokens that some models leak into output."""
    for token in ("<s>", "<|im_start|>", "<|im_end|>", "<|OUT|>"):
        text = text.replace(token, "")
    return text


def respond(message, history, model):
    """Stream a reply from OpenRouter for the given model + history.

    Supports both Gradio history formats so this works whether the
    installed Gradio version defaults ChatInterface to "messages"
    (list of {"role", "content"} dicts) or the older "tuples" format
    (list of [user_msg, bot_msg] pairs).
    """
    messages = []  # {"role": "system", "content": "You are a banking assistant."}
    for turn in history:
        if isinstance(turn, dict):
            messages.append({"role": turn["role"], "content": turn["content"]})
        else:
            user_msg, bot_msg = turn
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if bot_msg:
                messages.append({"role": "assistant", "content": bot_msg})
    messages.append({"role": "user", "content": message})

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
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


with gr.Blocks(title=APP_TITLE) as demo:
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
