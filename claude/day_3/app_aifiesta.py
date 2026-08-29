"""
AI Fiesta-style Gradio app: compare several OpenRouter models side by side.

Features:
- Compare mode: multiple chat windows shown in parallel columns, each running
  its own multi-turn conversation. One shared input box sends the same
  message to every active model, and all of them stream their replies at
  the same time (via background threads).
- Focus mode: the same conversations, but one model is shown large while the
  others collapse into small pill buttons you can click to switch focus.
- A checkbox row lets you pick which models are "active" (included when you
  send a message, and available to compare/focus on).
- "New Chat" clears every model's conversation and starts fresh.
"""

import os
import queue
import threading
import tomllib
from pathlib import Path

import gradio as gr
from openai import OpenAI

# --- Load the OpenRouter API key -------------------------------------------------
SECRETS_PATH = Path(__file__).parent.parent / "day_2" / "chatgpt" / ".streamlit" / "secrets.toml"

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
        "X-Title": "AI Fiesta",
    },
)

# --- Models being compared --------------------------------------------------------
MODELS = [
    "openai/gpt-oss-20b",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat-v3.1",
]
MODEL_LABELS = {
    "openai/gpt-oss-20b": "🧠 GPT-OSS 20B",
    "meta-llama/llama-3.3-70b-instruct": "🦙 Llama 3.3 70B",
    "deepseek/deepseek-chat-v3.1": "🐋 DeepSeek Chat",
}
LABEL_TO_MODEL = {label: model for model, label in MODEL_LABELS.items()}


def clean(text: str) -> str:
    for token in ("<s>", "<|im_start|>", "<|im_end|>", "<|OUT|>"):
        text = text.replace(token, "")
    return text


def stream_model(model, messages, q):
    """Runs in its own thread; pushes (model, partial_text, is_final) onto q."""
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            extra_headers={
                "HTTP-Referer": "http://localhost:7860",
                "X-Title": "AI Fiesta",
            },
            extra_body={"provider": {"data_collection": "deny"}},
        )
        partial = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                partial += clean(delta)
                q.put((model, partial, False))
        q.put((model, partial, True))
    except Exception as e:
        q.put((model, f"Error: {e}", True))


def send_message(message, active_labels, focused_model, histories):
    """Send `message` to every active model and stream all replies in parallel."""
    message = (message or "").strip()
    active_models = [LABEL_TO_MODEL[label] for label in active_labels] or MODELS

    if not message:
        yield (
            histories[MODELS[0]],
            histories[MODELS[1]],
            histories[MODELS[2]],
            histories[focused_model],
            histories,
            "",
        )
        return

    for m in active_models:
        histories[m] = histories[m] + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": ""},
        ]

    q = queue.Queue()
    threads = [
        threading.Thread(target=stream_model, args=(m, histories[m][:-1], q))
        for m in active_models
    ]
    for t in threads:
        t.start()

    remaining = set(active_models)
    while remaining:
        model, partial, finished = q.get()
        histories[model][-1]["content"] = partial
        if finished:
            remaining.discard(model)
        yield (
            histories[MODELS[0]],
            histories[MODELS[1]],
            histories[MODELS[2]],
            histories[focused_model],
            histories,
            "",
        )

    for t in threads:
        t.join()


def toggle_mode(mode):
    return gr.update(visible=(mode == "Compare")), gr.update(visible=(mode == "Focus"))


def toggle_columns(active_labels, prior_labels):
    """Update visibility for the chosen active models; never allow an empty selection."""
    if not active_labels:
        active_labels = prior_labels

    active_models = {LABEL_TO_MODEL[label] for label in active_labels}
    col_updates = [gr.update(visible=(m in active_models)) for m in MODELS]
    btn_updates = [gr.update(visible=(m in active_models)) for m in MODELS]
    checkbox_update = gr.update(value=active_labels)
    return [checkbox_update] + col_updates + btn_updates + [active_labels]


def switch_focus(target_model, histories):
    updates = [gr.update(variant=("primary" if m == target_model else "secondary")) for m in MODELS]
    return (histories[target_model], target_model, *updates)


def new_chat():
    fresh = {m: [] for m in MODELS}
    return (
        fresh[MODELS[0]],
        fresh[MODELS[1]],
        fresh[MODELS[2]],
        fresh[MODELS[0]],
        fresh,
        MODELS[0],
        "",
    )


CUSTOM_CSS = """
#msg-row { align-items: center; }
#controls-row { align-items: center; }
"""

with gr.Blocks(title="AI Fiesta", css=CUSTOM_CSS) as demo:
    with gr.Row():
        gr.Markdown("# 🎉 AI Fiesta (OpenRouter)")

    histories_state = gr.State({m: [] for m in MODELS})
    focused_model_state = gr.State(MODELS[0])
    active_models_state = gr.State(list(MODEL_LABELS.values()))

    with gr.Row():
        active_models_checkbox = gr.CheckboxGroup(
            choices=list(MODEL_LABELS.values()),
            value=list(MODEL_LABELS.values()),
            label="Active models",
        )

    with gr.Row(elem_id="controls-row"):
        with gr.Column(scale=8):
            mode_radio = gr.Radio(["Compare", "Focus"], value="Compare", show_label=False)
        with gr.Column(scale=1, min_width=120):
            new_chat_btn = gr.Button("🧹 New Chat")

    # --- Compare mode: all active models side by side -----------------------------
    with gr.Row(visible=True) as compare_view:
        compare_columns = {}
        compare_chatbots = {}
        for m in MODELS:
            with gr.Column() as col:
                gr.Markdown(f"**{MODEL_LABELS[m]}**")
                compare_chatbots[m] = gr.Chatbot(height=420, show_label=False)
            compare_columns[m] = col

    # --- Focus mode: one big chat + pill buttons to switch -------------------------
    with gr.Row(visible=False) as focus_view:
        with gr.Column(scale=4):
            focus_chatbot = gr.Chatbot(height=500, show_label=False)
        with gr.Column(scale=1):
            focus_buttons = {}
            for m in MODELS:
                focus_buttons[m] = gr.Button(
                    MODEL_LABELS[m],
                    variant=("primary" if m == MODELS[0] else "secondary"),
                )

    with gr.Row(elem_id="msg-row"):
        msg_box = gr.Textbox(
            placeholder="Message all active models...", show_label=False, scale=8
        )
        send_btn = gr.Button("Send", variant="primary", scale=1)

    compare_outputs = [compare_chatbots[m] for m in MODELS]
    submit_inputs = [msg_box, active_models_checkbox, focused_model_state, histories_state]
    submit_outputs = compare_outputs + [focus_chatbot, histories_state, msg_box]

    msg_box.submit(fn=send_message, inputs=submit_inputs, outputs=submit_outputs)
    send_btn.click(fn=send_message, inputs=submit_inputs, outputs=submit_outputs)

    mode_radio.change(fn=toggle_mode, inputs=mode_radio, outputs=[compare_view, focus_view])
    active_models_checkbox.change(
        fn=toggle_columns,
        inputs=[active_models_checkbox, active_models_state],
        outputs=[active_models_checkbox]
        + compare_outputs
        + [focus_buttons[m] for m in MODELS]
        + [active_models_state],
    )

    for m in MODELS:
        focus_buttons[m].click(
            fn=lambda histories, target=m: switch_focus(target, histories),
            inputs=histories_state,
            outputs=[focus_chatbot, focused_model_state] + [focus_buttons[x] for x in MODELS],
        )

    new_chat_btn.click(
        fn=new_chat,
        outputs=compare_outputs + [focus_chatbot, histories_state, focused_model_state, msg_box],
    )


if __name__ == "__main__":
    demo.launch()
