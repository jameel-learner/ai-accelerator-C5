"""
The agentic RAG step: instead of always stuffing retrieved chunks into the
prompt, the model gets two TOOLS and decides for itself which to call:

- search_documents: searches the local PDF vector store
- web_search: searches the live internet (DuckDuckGo, no API key)

This is the core "function calling / tool use" pattern - the model reads the
question, decides what it needs, calls a tool, reads the result, and either
calls another tool or answers. See _run_groq_loop / _run_claude_loop below
for the two providers' tool-calling wire formats.

On top of that, a deterministic CONFIDENCE GATE runs in code right after
every search_documents call (see _run_confidence_gate): if the best
retrieved chunk's similarity is below a threshold, web_search is
auto-triggered regardless of what the model decides. This replaces relying
purely on the model noticing (via SYSTEM_PROMPT wording) that its document
matches were too generic - that heuristic was observed to misfire (generic
passages got treated as "good enough" when they didn't address the actual
question). The model can still call web_search itself too; the gate only
forces the call it might otherwise skip.

Every stage - retrieval candidates, the gate's decision, each LLM
round-trip, each tool call, web results, and errors - is logged via
observability.py so it's inspectable per-query in the dashboard.
"""

import json
import os
import time
from dotenv import load_dotenv
import observability
from llm_config import get_active_provider_settings
from vector_store import VectorStore
from web_search import web_search as _web_search

load_dotenv()  # loads API keys + ACTIVE_PROVIDER from a .env file in the project root, if present

settings = get_active_provider_settings()
LLM_PROVIDER = settings.name
GROQ_MODEL = "llama-3.3-70b-versatile"
CLAUDE_MODEL = "claude-sonnet-4-6"
HUGGINGFACE_MODEL = settings.model if LLM_PROVIDER == "huggingface" else os.environ.get("HUGGINGFACE_MODEL", "Qwen/Qwen2.5-3B-Instruct")
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
GEMINI_MODEL = settings.model if LLM_PROVIDER == "gemini" else os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
OPENROUTER_MODEL = settings.model if LLM_PROVIDER == "openrouter" else os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

MAX_TOOL_ITERATIONS = 6  # safety cap so a confused agent can't loop forever

# Below this (1 - distance/2, in [0, 1]) the confidence gate auto-triggers
# web_search regardless of what the model decides. Tunable per-call via
# answer_question(confidence_threshold=...) - app.py exposes it as a slider.
DEFAULT_CONFIDENCE_THRESHOLD = 0.55

SYSTEM_PROMPT = """You are a helpful research assistant and teacher with two tools:

- search_documents: searches the user's uploaded PDF documents.
- web_search: searches the live internet.

Core behavior:
- Document-first policy: always search_documents first for questions that could be answered from the indexed PDFs.
- Never use web_search before search_documents when the document corpus could plausibly answer the question.
- Use web_search only as a fallback for missing facts, current information, dates, names, places, events, or if the document search returns no useful result.
- For short factual or explanatory questions, one good document search is often enough. Do not keep calling tools after you already have a clear answer.
- If the tool result clearly answers the question, stop and answer immediately.
- Never call the same tool with the same query twice in a row.
- Never loop between search_documents and web_search without a new reason.

Quality rules:
- Read what search_documents actually returned. If it does not specifically address every part of the question - especially named entities, places, dates, events, or specific context - treat it as insufficient and use web_search only if it is allowed and needed.
- Prefer the document answer over a web answer when both are available, unless the question clearly needs current information or the document is clearly incomplete.
- Only say "I don't have information about this in the available sources" after you have actually tried all available relevant tools and none answered the question.
- If web_search is not offered to you, do not pretend it exists.
- Never write fake tool calls or fabricated tool results as text. Only real tool calls count.
- Answer only from real tool results. Do not invent facts, page numbers, or web sources.
- After answering, clearly name the document with page number or the web page used.
- Keep answers concise unless the user asks for detail.
- The policy is: document-first, web as fallback, and never bypass the RAG pipeline when document results are available.
"""

TOOLS_SCHEMA = [
    {
        "name": "search_documents",
        "description": "Search the user's indexed PDF documents for relevant passages.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to search for"}},
            "required": ["query"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the live internet for current or general information.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to search for"}},
            "required": ["query"],
        },
    },
]


def _to_groq_tools(tools_schema: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools_schema
    ]


def _execute_tool(
    name: str,
    query_text: str,
    vector_store: VectorStore,
    top_k: int,
    doc_sources: list[str] | None,
    allowed_domains: list[str] | None,
    blocked_domains: list[str] | None,
) -> tuple[str, list[dict], list[dict], list[dict]]:
    """Runs a tool call. Returns (text_for_model, doc_chunks_used, web_results_used, all_candidates)."""
    if name == "search_documents":
        kept, discarded = vector_store.query_with_candidates(
            query_text, top_k=top_k, fetch_k=top_k * 3, sources=doc_sources
        )
        text = "\n\n".join(f"[{c['source']}, Page {c['page']}]\n{c['text']}" for c in kept)
        return text or "No relevant passages found in the documents.", kept, [], kept + discarded

    if name == "web_search":
        results = _web_search(query_text, max_results=5, allowed_domains=allowed_domains, blocked_domains=blocked_domains)
        text = "\n\n".join(f"[{r['title']}]({r['url']})\n{r['snippet']}" for r in results)
        return text or "No web results found.", [], results, []

    return f"Unknown tool: {name}", [], [], []


def _run_confidence_gate(
    query_text: str,
    confidence: float,
    threshold: float,
    web_enabled: bool,
    gate_state: dict,
    allowed_domains: list[str] | None,
    blocked_domains: list[str] | None,
    query_id: int,
    iteration: int,
    on_tool_call,
) -> tuple[str, list[dict]]:
    """
    Deterministic backstop: if document-retrieval confidence is below
    threshold and web_search hasn't already run this query, auto-trigger it
    in code rather than trusting the model to notice. Returns
    (extra_text_to_append, web_results) - both empty if the gate doesn't fire.
    """
    if gate_state["web_called"] or not web_enabled or confidence >= threshold:
        return "", []

    if on_tool_call:
        on_tool_call("web_search", query_text)

    t0 = time.perf_counter()
    results = _web_search(query_text, max_results=5, allowed_domains=allowed_domains, blocked_domains=blocked_domains)
    latency_ms = (time.perf_counter() - t0) * 1000
    text = "\n\n".join(f"[{r['title']}]({r['url']})\n{r['snippet']}" for r in results) or "No web results found."

    gate_state["web_called"] = True
    gate_state["auto_triggered"] = True

    observability.log_tool_call(query_id, iteration, "web_search", query_text, text, latency_ms, "auto_gate")
    observability.log_web_results(query_id, results)

    note = "\n\n[Auto-triggered web_search: document-retrieval confidence " \
           f"({confidence:.2f}) was below threshold ({threshold:.2f})]\n\n"
    return note + text, results


def _routing_path(doc_sources_used: list, web_sources_used: list) -> str:
    if doc_sources_used and web_sources_used:
        return "pdf_then_web"
    if doc_sources_used:
        return "pdf_only"
    if web_sources_used:
        return "web_only"
    return "none"


def _has_repeated_tool_cycle(trace: list[dict], tool_name: str, query_text: str, repeat_count: int = 2) -> bool:
    """Detect when the model keeps re-issuing the same tool call on the same query."""
    normalized_query = (query_text or "").strip()
    matches = 0
    for entry in reversed(trace):
        if entry.get("tool") == tool_name and str(entry.get("input", "")).strip() == normalized_query:
            matches += 1
            if matches >= repeat_count:
                return True
        else:
            # A different tool/query breaks the cycle pattern.
            matches = 0
    return False


def _groq_chat_with_retry(client, messages, tools, tool_choice, retries: int = 2):
    """
    Groq/Llama tool calling occasionally emits a malformed function-call tag
    (a model-side generation glitch, not something a prompt fix reliably
    prevents). Retry a couple times since it's often just a sampling fluke;
    returns None if it keeps failing so the caller can fall back gracefully
    instead of crashing.
    """
    from groq import BadRequestError

    for _ in range(retries + 1):
        try:
            return client.chat.completions.create(
                model=GROQ_MODEL, max_tokens=1000, messages=messages, tools=tools, tool_choice=tool_choice,
            )
        except BadRequestError as e:
            if "tool_use_failed" not in str(e):
                raise
    return None


def _run_groq_loop(question, vector_store, top_k, doc_sources, allowed_domains, blocked_domains,
                    web_enabled, threshold, query_id, on_tool_call, hard_fail_on_no_document=False):
    from groq import Groq, APIStatusError

    client = Groq()
    tools = _to_groq_tools(TOOLS_SCHEMA if web_enabled else TOOLS_SCHEMA[:1])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    doc_sources_used, web_sources_used, trace = [], [], []
    gate_state = {"web_called": False, "auto_triggered": False, "confidence": None}
    total_input_tokens = total_output_tokens = 0
    start_time = time.perf_counter()

    def _finish(answer, error=None):
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        observability.finish_query(
            query_id, answer, _routing_path(doc_sources_used, web_sources_used),
            gate_state["confidence"], threshold, gate_state["auto_triggered"],
            total_latency_ms, total_input_tokens, total_output_tokens, GROQ_MODEL, error=error,
        )
        return answer, doc_sources_used, web_sources_used, trace

    for iteration in range(MAX_TOOL_ITERATIONS):
        # Force a real tool call on the first turn - the model would sometimes
        # just narrate a fake "search" in plain text instead of actually
        # calling a tool, which defeats the entire "answer only from tool
        # results" premise. After the first turn it's free to conclude.
        tool_choice = "required" if iteration == 0 else "auto"
        t0 = time.perf_counter()
        try:
            response = _groq_chat_with_retry(client, messages, tools, tool_choice)
            if response is None:
                # Tool calling kept failing - fall back to a plain answer so
                # the user still gets something instead of a crash.
                fallback_messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
                response = client.chat.completions.create(model=GROQ_MODEL, max_tokens=1000, messages=fallback_messages)
                latency_ms = (time.perf_counter() - t0) * 1000
                usage = response.usage
                total_input_tokens += usage.prompt_tokens
                total_output_tokens += usage.completion_tokens
                observability.log_llm_call(
                    query_id, iteration, fallback_messages, GROQ_MODEL, {"max_tokens": 1000},
                    response.choices[0].message.content, response.choices[0].finish_reason,
                    usage.prompt_tokens, usage.completion_tokens, latency_ms,
                )
                return _finish(response.choices[0].message.content)
        except APIStatusError as e:
            note = "rate limit" if e.status_code == 429 else f"API error ({e.status_code})"
            answer = f"Sorry, I hit a Groq {note} while working on this - please try again shortly."
            observability.log_error(query_id, "llm", str(e))
            return _finish(answer, error=str(e))

        latency_ms = (time.perf_counter() - t0) * 1000
        msg = response.choices[0].message
        usage = response.usage
        total_input_tokens += usage.prompt_tokens
        total_output_tokens += usage.completion_tokens
        observability.log_llm_call(
            query_id, iteration, messages, GROQ_MODEL, {"max_tokens": 1000, "tool_choice": tool_choice},
            msg.content, response.choices[0].finish_reason, usage.prompt_tokens, usage.completion_tokens, latency_ms,
        )

        if not msg.tool_calls:
            return _finish(msg.content)

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            query_text = args.get("query", "")
            if tc.function.name == "web_search":
                gate_state["web_called"] = True
            if on_tool_call:
                on_tool_call(tc.function.name, query_text)
            trace.append({"tool": tc.function.name, "input": query_text})

            t_tool = time.perf_counter()
            result_text, chunks, web_results, candidates = _execute_tool(
                tc.function.name, query_text, vector_store, top_k, doc_sources, allowed_domains, blocked_domains
            )
            tool_latency_ms = (time.perf_counter() - t_tool) * 1000
            observability.log_tool_call(query_id, iteration, tc.function.name, query_text, result_text, tool_latency_ms, "llm")

            if _has_repeated_tool_cycle(trace, tc.function.name, query_text):
                return _finish(
                    "The model kept reusing the same tool call, so I stopped the loop and returned the latest result instead of waiting forever.\n\n"
                    f"{result_text[:2000]}"
                )

            if tc.function.name == "search_documents":
                observability.log_retrieval_candidates(query_id, iteration, candidates)
                confidence = chunks[0]["confidence"] if chunks else 0.0
                if gate_state["confidence"] is None:
                    gate_state["confidence"] = confidence
                extra_text, extra_web = _run_confidence_gate(
                    query_text, confidence, threshold, web_enabled, gate_state,
                    allowed_domains, blocked_domains, query_id, iteration, on_tool_call,
                )
                result_text += extra_text
                web_results = web_results + extra_web
                if extra_text:
                    trace.append({"tool": "web_search", "input": query_text})

            doc_sources_used.extend(chunks)
            web_sources_used.extend(web_results)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

    observability.log_error(query_id, "other", "tool-call iteration limit reached")
    return _finish("I wasn't able to finish within the tool-call limit.")


def _run_claude_loop(question, vector_store, top_k, doc_sources, allowed_domains, blocked_domains,
                      web_enabled, threshold, query_id, on_tool_call, hard_fail_on_no_document=False):
    from anthropic import Anthropic, APIStatusError

    client = Anthropic()
    tools = TOOLS_SCHEMA if web_enabled else TOOLS_SCHEMA[:1]
    messages = [{"role": "user", "content": question}]
    doc_sources_used, web_sources_used, trace = [], [], []
    gate_state = {"web_called": False, "auto_triggered": False, "confidence": None}
    total_input_tokens = total_output_tokens = 0
    start_time = time.perf_counter()

    def _finish(answer, error=None):
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        observability.finish_query(
            query_id, answer, _routing_path(doc_sources_used, web_sources_used),
            gate_state["confidence"], threshold, gate_state["auto_triggered"],
            total_latency_ms, total_input_tokens, total_output_tokens, CLAUDE_MODEL, error=error,
        )
        return answer, doc_sources_used, web_sources_used, trace

    for iteration in range(MAX_TOOL_ITERATIONS):
        # Force a real tool call on the first turn (see matching comment in
        # _run_groq_loop) so the model can't just narrate a fake search.
        tool_choice = {"type": "any"} if iteration == 0 else {"type": "auto"}
        t0 = time.perf_counter()
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL, max_tokens=1000, system=SYSTEM_PROMPT, tools=tools,
                tool_choice=tool_choice, messages=messages,
            )
        except APIStatusError as e:
            note = "rate limit" if e.status_code == 429 else f"API error ({e.status_code})"
            answer = f"Sorry, I hit a Claude {note} while working on this - please try again shortly."
            observability.log_error(query_id, "llm", str(e))
            return _finish(answer, error=str(e))

        latency_ms = (time.perf_counter() - t0) * 1000
        usage = response.usage
        total_input_tokens += usage.input_tokens
        total_output_tokens += usage.output_tokens
        response_text = next((b.text for b in response.content if b.type == "text"), None)
        observability.log_llm_call(
            query_id, iteration, messages, CLAUDE_MODEL, {"max_tokens": 1000, "tool_choice": tool_choice},
            response_text, response.stop_reason, usage.input_tokens, usage.output_tokens, latency_ms,
        )

        if response.stop_reason != "tool_use":
            return _finish(response_text or "")

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            args = block.input
            query_text = args.get("query", "")
            if block.name == "web_search":
                gate_state["web_called"] = True
            if on_tool_call:
                on_tool_call(block.name, query_text)
            trace.append({"tool": block.name, "input": query_text})

            t_tool = time.perf_counter()
            result_text, chunks, web_results, candidates = _execute_tool(
                block.name, query_text, vector_store, top_k, doc_sources, allowed_domains, blocked_domains
            )
            tool_latency_ms = (time.perf_counter() - t_tool) * 1000
            observability.log_tool_call(query_id, iteration, block.name, query_text, result_text, tool_latency_ms, "llm")

            if _has_repeated_tool_cycle(trace, block.name, query_text):
                return _finish(
                    "The model kept reusing the same tool call, so I stopped the loop and returned the latest result instead of waiting forever.\n\n"
                    f"{result_text[:2000]}"
                )

            if block.name == "search_documents":
                observability.log_retrieval_candidates(query_id, iteration, candidates)
                if hard_fail_on_no_document and not chunks:
                    return _finish(
                        "I could not find a relevant answer in the indexed documents. This query is configured to stop without web fallback."
                    )
                confidence = chunks[0]["confidence"] if chunks else 0.0
                if gate_state["confidence"] is None:
                    gate_state["confidence"] = confidence
                extra_text, extra_web = _run_confidence_gate(
                    query_text, confidence, threshold, web_enabled, gate_state,
                    allowed_domains, blocked_domains, query_id, iteration, on_tool_call,
                )
                result_text += extra_text
                web_results = web_results + extra_web
                if extra_text:
                    trace.append({"tool": "web_search", "input": query_text})

            doc_sources_used.extend(chunks)
            web_sources_used.extend(web_results)
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result_text})

        messages.append({"role": "user", "content": tool_results})

    observability.log_error(query_id, "other", "tool-call iteration limit reached")
    return _finish("I wasn't able to finish within the tool-call limit.")


def _run_huggingface_loop(question, vector_store, top_k, doc_sources, allowed_domains, blocked_domains,
                         web_enabled, threshold, query_id, on_tool_call, hard_fail_on_no_document=False):
    from huggingface_hub import InferenceClient

    client = InferenceClient(model=HUGGINGFACE_MODEL, token=HF_TOKEN, provider="featherless-ai")
    tools = TOOLS_SCHEMA if web_enabled else TOOLS_SCHEMA[:1]
    messages = [{"role": "user", "content": question}]
    doc_sources_used, web_sources_used, trace = [], [], []
    gate_state = {"web_called": False, "auto_triggered": False, "confidence": None}
    total_input_tokens = total_output_tokens = 0
    start_time = time.perf_counter()

    def _finish(answer, error=None):
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        observability.finish_query(
            query_id, answer, _routing_path(doc_sources_used, web_sources_used),
            gate_state["confidence"], threshold, gate_state["auto_triggered"],
            total_latency_ms, total_input_tokens, total_output_tokens, HUGGINGFACE_MODEL, error=error,
        )
        return answer, doc_sources_used, web_sources_used, trace

    for iteration in range(MAX_TOOL_ITERATIONS):
        tool_choice = "required" if iteration == 0 else "auto"
        t0 = time.perf_counter()
        try:
            response = client.chat_completion(
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
                model=HUGGINGFACE_MODEL,
                max_tokens=1000,
                tools=tools,
                tool_choice=tool_choice,
            )
        except Exception as e:
            note = "rate limit" if "429" in str(e) or "rate limit" in str(e).lower() else "API error"
            answer = f"Sorry, I hit a Hugging Face {note} while working on this - please try again shortly."
            observability.log_error(query_id, "llm", str(e))
            return _finish(answer, error=str(e))

        latency_ms = (time.perf_counter() - t0) * 1000
        message = getattr(response, "choices", [None])[0].message if getattr(response, "choices", None) else None
        if message is None:
            answer = getattr(response, "content", "") or "I couldn't get a valid model response."
            return _finish(answer)

        total_input_tokens += getattr(response, "usage", {}).get("prompt_tokens", 0) or 0
        total_output_tokens += getattr(response, "usage", {}).get("completion_tokens", 0) or 0
        observability.log_llm_call(
            query_id, iteration, messages, HUGGINGFACE_MODEL, {"max_tokens": 1000, "tool_choice": tool_choice},
            getattr(message, "content", None), getattr(response, "finish_reason", None),
            getattr(response, "usage", {}).get("prompt_tokens", 0), getattr(response, "usage", {}).get("completion_tokens", 0), latency_ms,
        )

        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            return _finish(getattr(message, "content", "") or "")

        messages.append({"role": "assistant", "content": getattr(message, "content", None), "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in tool_calls
        ]})

        for tc in tool_calls:
            args = json.loads(tc.function.arguments)
            query_text = args.get("query", "")
            if tc.function.name == "web_search":
                gate_state["web_called"] = True
            if on_tool_call:
                on_tool_call(tc.function.name, query_text)
            trace.append({"tool": tc.function.name, "input": query_text})

            t_tool = time.perf_counter()
            result_text, chunks, web_results, candidates = _execute_tool(
                tc.function.name, query_text, vector_store, top_k, doc_sources, allowed_domains, blocked_domains
            )
            tool_latency_ms = (time.perf_counter() - t_tool) * 1000
            observability.log_tool_call(query_id, iteration, tc.function.name, query_text, result_text, tool_latency_ms, "llm")

            if _has_repeated_tool_cycle(trace, tc.function.name, query_text):
                return _finish(
                    "The model kept reusing the same tool call, so I stopped the loop and returned the latest result instead of waiting forever.\n\n"
                    f"{result_text[:2000]}"
                )

            if tc.function.name == "search_documents":
                observability.log_retrieval_candidates(query_id, iteration, candidates)
                confidence = chunks[0]["confidence"] if chunks else 0.0
                if gate_state["confidence"] is None:
                    gate_state["confidence"] = confidence
                extra_text, extra_web = _run_confidence_gate(
                    query_text, confidence, threshold, web_enabled, gate_state,
                    allowed_domains, blocked_domains, query_id, iteration, on_tool_call,
                )
                result_text += extra_text
                web_results = web_results + extra_web
                if extra_text:
                    trace.append({"tool": "web_search", "input": query_text})

            doc_sources_used.extend(chunks)
            web_sources_used.extend(web_results)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

    observability.log_error(query_id, "other", "tool-call iteration limit reached")
    return _finish("I wasn't able to finish within the tool-call limit.")


def _to_gemini_tools(tools_schema: list[dict]):
    from google.generativeai import types

    declarations = []
    for t in tools_schema:
        declarations.append(types.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=t["input_schema"],
        ))
    return [types.Tool(function_declarations=declarations)]


def _run_gemini_loop(question, vector_store, top_k, doc_sources, allowed_domains, blocked_domains,
                    web_enabled, threshold, query_id, on_tool_call, hard_fail_on_no_document=False):
    import google.generativeai as genai

    if not GOOGLE_API_KEY:
        return _finish_error(query_id, "Gemini API key is missing.")

    genai.configure(api_key=GOOGLE_API_KEY)
    tools = _to_gemini_tools(TOOLS_SCHEMA if web_enabled else TOOLS_SCHEMA[:1])
    model = genai.GenerativeModel(model_name=GEMINI_MODEL, tools=tools, system_instruction=SYSTEM_PROMPT)

    doc_sources_used, web_sources_used, trace = [], [], []
    gate_state = {"web_called": False, "auto_triggered": False, "confidence": None}
    total_input_tokens = total_output_tokens = 0
    start_time = time.perf_counter()

    def _finish(answer, error=None):
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        observability.finish_query(
            query_id, answer, _routing_path(doc_sources_used, web_sources_used),
            gate_state["confidence"], threshold, gate_state["auto_triggered"],
            total_latency_ms, total_input_tokens, total_output_tokens, GEMINI_MODEL, error=error,
        )
        return answer, doc_sources_used, web_sources_used, trace

    for iteration in range(MAX_TOOL_ITERATIONS):
        try:
            response = model.generate_content(question)
        except Exception as e:
            note = "rate limit" if "429" in str(e) or "rate limit" in str(e).lower() else "API error"
            answer = f"Sorry, I hit a Gemini {note} while working on this - please try again shortly."
            observability.log_error(query_id, "llm", str(e))
            return _finish(answer, error=str(e))

        parts = getattr(response.candidates[0].content, "parts", []) if getattr(response, "candidates", None) else []
        if not parts:
            text = getattr(response, "text", "") or ""
            return _finish(text or "I couldn't get a valid Gemini response.")

        function_calls = []
        text_parts = []
        for part in parts:
            if hasattr(part, "function_call") and getattr(part, "function_call", None):
                function_calls.append(part.function_call)
            elif getattr(part, "text", None):
                text_parts.append(part.text)

        if not function_calls:
            return _finish("\n".join(text_parts) or "")

        for fc in function_calls:
            args = getattr(fc, "args", {}) or {}
            query_text = args.get("query", "")
            tool_name = getattr(fc, "name", "")
            if on_tool_call:
                on_tool_call(tool_name, query_text)
            trace.append({"tool": tool_name, "input": query_text})

            t_tool = time.perf_counter()
            result_text, chunks, web_results, candidates = _execute_tool(
                tool_name, query_text, vector_store, top_k, doc_sources, allowed_domains, blocked_domains
            )
            tool_latency_ms = (time.perf_counter() - t_tool) * 1000
            observability.log_tool_call(query_id, iteration, tool_name, query_text, result_text, tool_latency_ms, "llm")

            if _has_repeated_tool_cycle(trace, tool_name, query_text):
                return _finish(
                    "The model kept reusing the same tool call, so I stopped the loop and returned the latest result instead of waiting forever.\n\n"
                    f"{result_text[:2000]}"
                )

            if tool_name == "search_documents":
                observability.log_retrieval_candidates(query_id, iteration, candidates)
                if hard_fail_on_no_document and not chunks:
                    return _finish(
                        "I could not find a relevant answer in the indexed documents. This query is configured to stop without web fallback."
                    )
                confidence = chunks[0]["confidence"] if chunks else 0.0
                if gate_state["confidence"] is None:
                    gate_state["confidence"] = confidence
                extra_text, extra_web = _run_confidence_gate(
                    query_text, confidence, threshold, web_enabled, gate_state,
                    allowed_domains, blocked_domains, query_id, iteration, on_tool_call,
                )
                result_text += extra_text
                web_results = web_results + extra_web
                if extra_text:
                    trace.append({"tool": "web_search", "input": query_text})

            doc_sources_used.extend(chunks)
            web_sources_used.extend(web_results)
            response = model.generate_content(
                [
                    {"role": "user", "parts": [{"text": question}]},
                    {"role": "function", "parts": [{"function_response": {"name": tool_name, "response": {"content": result_text}}}]},
                ]
            )

            parts = getattr(response.candidates[0].content, "parts", []) if getattr(response, "candidates", None) else []
            final_text = "\n".join(part.text for part in parts if getattr(part, "text", None))
            if final_text:
                return _finish(final_text)

    observability.log_error(query_id, "other", "tool-call iteration limit reached")
    return _finish("I wasn't able to finish within the tool-call limit.")


def _run_openrouter_loop(question, vector_store, top_k, doc_sources, allowed_domains, blocked_domains,
                        web_enabled, threshold, query_id, on_tool_call, hard_fail_on_no_document=False):
    import requests

    if not OPENROUTER_API_KEY:
        return "OpenRouter API key is missing. Set OPENROUTER_API_KEY in your .env file.", [], [], []

    doc_text, chunks, web_results, candidates = _execute_tool(
        "search_documents", question, vector_store, top_k, doc_sources, allowed_domains, blocked_domains
    )
    if hard_fail_on_no_document and not chunks:
        return "I could not find a relevant answer in the indexed documents. This query is configured to stop without web fallback.", [], [], []
    if web_enabled:
        web_text, web_chunks, web_result_rows, web_candidates = _execute_tool(
            "web_search", question, vector_store, top_k, doc_sources, allowed_domains, blocked_domains
        )
        if web_text and web_text != "No web results found.":
            doc_text = f"{doc_text}\n\n{web_text}"

    system_message = SYSTEM_PROMPT + "\n\nUse the knowledge in the context below. If the information is insufficient, say so clearly."
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Question: {question}\n\nContext:\n{doc_text}"},
        ],
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "Edukripa RAG",
        },
        json=payload,
        timeout=120,
    )
    if response.status_code >= 400:
        msg = response.text[:500]
        return f"Sorry, I hit an OpenRouter API error ({response.status_code}): {msg}", [], [], []

    output = response.json()
    answer = output["choices"][0]["message"]["content"] or "The model ran out of budget while reasoning and returned no answer. Please try again."
    return answer, chunks, web_results or [], []


def _finish_error(query_id, message):
    return message, [], [], []


def answer_question(
    vector_store: VectorStore,
    question: str,
    top_k: int = 5,
    doc_sources: list[str] | None = None,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
    web_enabled: bool = True,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    hard_fail_on_no_document: bool = False,
    session_id: str = "default",
    on_tool_call=None,
) -> dict:
    """
    doc_sources: restrict search_documents to these filenames (None/empty = all indexed docs)
    allowed_domains/blocked_domains: restrict web_search results (None/empty = unrestricted)
    web_enabled: if False, the model only gets the search_documents tool
    confidence_threshold: below this, web_search is auto-triggered by code
        after search_documents runs, regardless of what the model decides
    session_id: groups queries together for the observability dashboard
    on_tool_call: optional callback(tool_name, query) fired the moment each tool call is dispatched
    """
    if LLM_PROVIDER == "claude":
        loop, model = _run_claude_loop, CLAUDE_MODEL
    elif LLM_PROVIDER == "groq":
        loop, model = _run_groq_loop, GROQ_MODEL
    elif LLM_PROVIDER == "huggingface":
        loop, model = _run_huggingface_loop, HUGGINGFACE_MODEL
    elif LLM_PROVIDER == "gemini":
        loop, model = _run_gemini_loop, GEMINI_MODEL
    elif LLM_PROVIDER == "openrouter":
        loop, model = _run_openrouter_loop, OPENROUTER_MODEL
    else:
        raise ValueError(f"Unknown LLM_PROVIDER {LLM_PROVIDER!r} (expected 'groq', 'claude', 'huggingface', 'gemini', or 'openrouter')")

    query_id = observability.start_query(session_id, question, LLM_PROVIDER, model)

    answer, docs, webs, trace = loop(
        question, vector_store, top_k, doc_sources, allowed_domains, blocked_domains,
        web_enabled, confidence_threshold, query_id, on_tool_call, hard_fail_on_no_document,
    )

    return {
        "answer": answer,
        "doc_sources": [
            {"source": c["source"], "page": c["page"], "distance": round(c["distance"], 3), "text": c["text"]}
            for c in docs
        ],
        "web_sources": webs,
        "trace": trace,
        "query_id": query_id,
    }


if __name__ == "__main__":
    import sys
    import uuid

    sys.stdout.reconfigure(encoding="utf-8")  # avoid UnicodeEncodeError on Windows' default cp1252 console

    if LLM_PROVIDER == "groq":
        required_key = "GROQ_API_KEY"
    elif LLM_PROVIDER == "claude":
        required_key = "ANTHROPIC_API_KEY"
    elif LLM_PROVIDER == "huggingface":
        required_key = "HF_TOKEN"
    elif LLM_PROVIDER == "gemini":
        required_key = "GOOGLE_API_KEY"
    elif LLM_PROVIDER == "openrouter":
        required_key = "OPENROUTER_API_KEY"
    else:
        required_key = None

    if required_key and not (os.environ.get(required_key) or os.environ.get("GEMINI_API_KEY") or os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")):
        print(f"ERROR: LLM_PROVIDER={LLM_PROVIDER!r} but {required_key} is not set. Add it to .env.")
        sys.exit(1)

    store = VectorStore()
    if store.collection.count() == 0:
        print("No chunks in the vector store yet. Run main.py first to index a PDF.")
        sys.exit(1)

    cli_session_id = f"cli-{uuid.uuid4().hex[:8]}"
    print(f"RAG agent ready (provider: {LLM_PROVIDER}). Type a question (or 'quit' to exit).\n")
    while True:
        q = input("You: ").strip()
        if q.lower() in ("quit", "exit"):
            break

        def _on_tool_call(name, query):
            icon = "🔍" if name == "web_search" else "📄"
            print(f"  {icon} {name}({query!r})")

        result = answer_question(store, q, session_id=cli_session_id, on_tool_call=_on_tool_call)
        print(f"\n{LLM_PROVIDER.capitalize()}: {result['answer']}")
        if result["doc_sources"]:
            labels = ", ".join(f"{s['source']} p.{s['page']}" for s in result["doc_sources"])
            print(f"(doc sources: {labels})")
        if result["web_sources"]:
            labels = ", ".join(f"{s['title']} ({s['url']})" for s in result["web_sources"])
            print(f"(web sources: {labels})")
        print()
