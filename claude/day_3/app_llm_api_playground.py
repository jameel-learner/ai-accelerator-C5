"""
LLM-as-API Playground
----------------------
A Streamlit front end for the four "LLM steered as an API" demos
(analyze_feedback, classify_support_ticket, extract_invoice_fields,
generate_seo_meta) — all self-contained in this same day_3 folder.

Pick one of the four "API features" in the sidebar, chat with it, and watch
the JSON response stream in live. Each feature also ships 5 sample prompts
in a collapsible section under the chat box.
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st
# from dotenv import load_dotenv
from openai import OpenAI

# ── Wire up the feature modules (kept alongside this app) ───────────────────

# APP_DIR = Path(__file__).resolve().parent
# if str(APP_DIR) not in sys.path:
#     sys.path.insert(0, str(APP_DIR))

# load_dotenv(APP_DIR / ".env")

import analyze_feedback as feat_feedback  # noqa: E402
import classify_support_ticket as feat_ticket  # noqa: E402
import extract_invoice_fields as feat_invoice  # noqa: E402
import generate_seo_meta as feat_seo  # noqa: E402

# ── Page setup ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="LLM-as-API Playground", page_icon="🧩", layout="wide")

# Initialize the OpenAI client with OpenRouter
api_key = st.secrets.get("OPENROUTER_API_KEY")
if not api_key:
    st.error("Missing OPENROUTER_API_KEY. Add it to .streamlit/secrets.toml.")
    st.stop()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    default_headers={
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "My ChatBot",
    },
)
# client = OpenAI(
#     api_key=os.environ.get("OPENROUTER_API_KEY"),
#     base_url="https://openrouter.ai/api/v1",
# )


# ── Feature registry ──────────────────────────────────────────────────────────

FEATURES = {
    "Analyze Customer Feedback": {
        "module": feat_feedback,
        "icon": "💬",
        "description": "Turns raw customer feedback into sentiment, intent, urgency and a suggested next action.",
        "needs_payload": True,
        "chat_placeholder": "Paste a piece of customer feedback...",
        "samples": [
            "The mobile app freezes every time I upload a photo larger than 5MB. This has happened three times this week and I'm about to cancel my subscription.",
            "Just wanted to say the new onboarding flow is fantastic - way less confusing than before, and I invited my whole team in minutes.",
            "Is there a way to export reports as CSV instead of only PDF? Would really help with our internal analysis.",
            "I was charged twice for my annual plan and support hasn't replied in 4 days. This is extremely frustrating and needs to be resolved urgently.",
            "The search feature is decent but sometimes doesn't return obviously relevant results. Not a huge deal, just something worth improving.",
        ],
    },
    "Classify Support Ticket": {
        "module": feat_ticket,
        "icon": "🎫",
        "description": "Routes a raw support ticket to the right department, assigns priority, and drafts a reply.",
        "needs_payload": False,
        "chat_placeholder": "Paste a support ticket...",
        "samples": [
            "Subject: Charged twice for the same order! I placed order #ORD-88231 on Sunday and see two charges of ₹2,499 on my card. I need an immediate refund for the duplicate charge.",
            "Our entire team has been locked out of the platform since 9 AM. We're getting a 503 error on every page and have a client demo at 2 PM. Please escalate immediately.",
            "Hi there, I forgot how to change my profile picture on the app. I've looked in settings but can't find it. Can you guide me?",
            "It would be great if you could add a dark mode to the mobile app. A lot of us use it late at night and the white background is harsh on the eyes. Not urgent at all.",
            "My package was supposed to arrive 5 days ago and the tracking page hasn't updated since. Can someone tell me where it actually is?",
        ],
    },
    "Extract Invoice Fields": {
        "module": feat_invoice,
        "icon": "🧾",
        "description": "Extracts structured fields (vendor, line items, totals, dates) from raw invoice text.",
        "needs_payload": False,
        "chat_placeholder": "Paste raw invoice text, OCR output, or an invoice email...",
        "samples": [
            "INVOICE\nInvoice No: INV-2024-0892\nDate: 15 March 2024\nDue Date: 14 April 2024\nFrom: TechSolutions Pvt Ltd, tech@techsolutions.in\nBill To: Acme Corp\nUI/UX Design Services 1 x ₹45,000 = ₹45,000\nAPI Integration 2 x ₹12,000 = ₹24,000\nSubtotal: ₹69,000 | GST (18%): ₹12,420 | Total: ₹81,420\nPayment Terms: Net 30",
            "Hi Ramesh, please find the invoice for last month. Invoice #: 007 | Issued: Jan 5 2024. Content writing: 8 articles x $50 = $400. Social captions: 30 posts x $10 = $300. Subtotal: $700, Tax: $59.50, TOTAL DUE: $759.50. Pay within 15 days.",
            "Invoice from Raj Electricals. Date: 22-02-2024. Customer: Mr. Ahmed. Wiring work for 2BHK apartment ₹15,000. Materials (wire, switches) ₹4,200. Total: ₹19,200. Cash payment preferred.",
            "Bill To: Globex LLC. Vendor: CloudHost Inc, billing@cloudhost.com. Plan: Business Tier, Jan 2024 - $199.00. Add-on: Extra storage 500GB - $25.00. Subtotal $224.00, Tax 8% $17.92, Total $241.92. Due on receipt.",
            "Just a note about the weather today, sunny with a chance of rain later this afternoon.",
        ],
    },
    "Generate SEO Meta": {
        "module": feat_seo,
        "icon": "🔍",
        "description": "Generates SEO title, meta description, keywords, slug and schema type for an article.",
        "needs_payload": False,
        "chat_placeholder": "Paste the full body of an article or blog post...",
        "samples": [
            "What is RAG? Retrieval-Augmented Generation (RAG) combines large language models with external knowledge bases, fetching relevant documents at query time to generate more accurate, up-to-date answers instead of relying purely on training data. It works in two steps: retrieval from a vector database, then generation grounded in the retrieved context. RAG reduces hallucination and is widely used in enterprise chatbots, customer support, legal search, and medical information retrieval.",
            "10 Science-Backed Benefits of Walking 10,000 Steps a Day. Walking is one of the simplest, most accessible forms of exercise, yet research shows it dramatically improves cardiovascular health, aids weight management, reduces the risk of type 2 diabetes, boosts mood by releasing endorphins, and strengthens bones and joints. Start with 5,000 steps and build up gradually using a fitness tracker to monitor progress.",
            "BrewMaster Pro 3000 - Automatic Coffee Maker with Built-in Grinder. A premium automatic coffee machine for coffee lovers who demand café-quality espresso and filter coffee at home. Features a built-in conical burr grinder, 15-bar pressure pump, 1.8-litre water tank, programmable auto-brew timer, and milk frother. Backed by a 2-year warranty and free shipping across India. Price ₹18,999.",
            "Beginner's Guide to Indoor Container Gardening. Growing vegetables and herbs indoors is easier than most people think. This guide covers choosing the right containers, picking a sunny window or grow light, soil and drainage basics, watering schedules, and the best beginner-friendly plants like basil, mint, cherry tomatoes and lettuce for a small apartment setup.",
            "5 Budget Travel Hacks for Backpacking Through Southeast Asia. Southeast Asia remains one of the most affordable regions to backpack, but costs add up fast without a plan. Book flights in incognito mode to avoid dynamic pricing, travel during shoulder season for lower hostel rates, use overnight buses and trains to save on a night's accommodation, eat at local street stalls instead of tourist-district restaurants, and negotiate multi-day tour bundles upfront rather than booking day by day.",
        ],
    },
}

# ── Session state ─────────────────────────────────────────────────────────────

if "chats" not in st.session_state:
    st.session_state.chats = {name: [] for name in FEATURES}

if "feedback_meta" not in st.session_state:
    st.session_state.feedback_meta = {"product_name": "Our Product", "language": "en"}

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# ── Sidebar: feature picker ──────────────────────────────────────────────────

st.sidebar.title("🧩 LLM-as-API Playground")
st.sidebar.caption(
    "Four demos of steering an LLM into a strict, structured API with nothing "
    "but a system prompt. Pick one and chat with it."
)

feature_name = st.sidebar.radio(
    "API feature",
    list(FEATURES.keys()),
    format_func=lambda name: f"{FEATURES[name]['icon']}  {name}",
)
feature = FEATURES[feature_name]

if feature["needs_payload"]:
    st.sidebar.divider()
    st.sidebar.subheader("Payload fields")
    st.session_state.feedback_meta["product_name"] = st.sidebar.text_input(
        "Product name", value=st.session_state.feedback_meta["product_name"]
    )
    st.session_state.feedback_meta["language"] = st.sidebar.selectbox(
        "Language", ["en", "hi", "auto"],
        index=["en", "hi", "auto"].index(st.session_state.feedback_meta["language"]),
    )

if st.sidebar.button("🗑️ Clear this chat"):
    st.session_state.chats[feature_name] = []
    st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────

st.title(f"{feature['icon']} {feature_name}")
st.caption(feature["description"])

with st.expander("View the system prompt (the API contract)"):
    st.code(feature["module"].SYSTEM_PROMPT, language="text")

# Render existing chat history for this feature
for msg in st.session_state.chats[feature_name]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


def build_user_content(feature: dict, text: str) -> str:
    """Shape the chat text the way each day_1 module expects its input."""
    if feature["needs_payload"]:
        payload = {
            "feedback_text": text,
            "product_name": st.session_state.feedback_meta["product_name"],
            "language": st.session_state.feedback_meta["language"],
        }
        return json.dumps(payload)
    return text


def stream_completion(system_prompt: str, model: str, user_content: str):
    stream = client.chat.completions.create(
        model=model,
        temperature=0,
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def handle_user_input(user_text: str) -> None:
    st.session_state.chats[feature_name].append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    user_content = build_user_content(feature, user_text)

    with st.chat_message("assistant"):
        if not os.environ.get("OPENROUTER_API_KEY"):
            error_msg = (
                "⚠️ OPENROUTER_API_KEY is not set. Add it to `claude/day_3/.env` "
                "and restart the app."
            )
            st.error(error_msg)
            st.session_state.chats[feature_name].append(
                {"role": "assistant", "content": error_msg}
            )
            return

        try:
            full_response = st.write_stream(
                stream_completion(
                    feature["module"].SYSTEM_PROMPT,
                    feature["module"].MODEL,
                    user_content,
                )
            )
        except Exception as exc:  # noqa: BLE001
            error_msg = f"⚠️ Request failed: {exc}"
            st.error(error_msg)
            st.session_state.chats[feature_name].append(
                {"role": "assistant", "content": error_msg}
            )
            return

        raw = full_response.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            parsed = json.loads(raw)
            with st.expander("View parsed JSON"):
                st.json(parsed)
        except (json.JSONDecodeError, ValueError):
            st.caption("⚠️ Response could not be parsed as JSON.")

    st.session_state.chats[feature_name].append(
        {"role": "assistant", "content": full_response}
    )


# Process a sample prompt clicked in the expander below (queued last run)
if st.session_state.pending_prompt is not None:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    handle_user_input(prompt)

# ── Sample prompts section (collapsed by default) ────────────────────────────

with st.expander("💡 5 sample prompts for this feature", expanded=False):
    for i, sample in enumerate(feature["samples"], start=1):
        cols = st.columns([8, 1])
        cols[0].markdown(f"**{i}.** {sample}")
        if cols[1].button("Use", key=f"sample_{feature_name}_{i}"):
            st.session_state.pending_prompt = sample
            st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────

prompt = st.chat_input(feature["chat_placeholder"])
if prompt:
    handle_user_input(prompt)
