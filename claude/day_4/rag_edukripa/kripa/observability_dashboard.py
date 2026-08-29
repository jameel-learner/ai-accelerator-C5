"""
Observability / debug dashboard for the RAG agent - rendered as a section
of the host page (src/app.py), not a separate Streamlit page, since the
dashboard IS the host page now and chat moved into the floating widget.

Reads everything logged by observability.py (per-query retrieval
candidates - kept and discarded, LLM I/O, tool calls, web fallback
results, errors) plus the vector store's chunk metadata, and surfaces it
for inspection: which path a query took and why (the confidence-gate
routing decision), what got retrieved vs. discarded, exactly what was
sent to the LLM, cost/latency, and basic usage analytics.
"""

from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import observability
from vector_store import VectorStore

# Fixed categorical order (one hue per routing path) so a filter never
# repaints colors, plus a status pair for the confidence/threshold bar.
# See dataviz skill's reference palette.
CATEGORICAL = {
    "pdf_only": "#2a78d6",      # blue
    "web_only": "#eb6834",      # orange
    "pdf_then_web": "#1baf7a",  # aqua
    "none": "#eda100",          # yellow
}
SEQUENTIAL_BLUE = "#3987e5"
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"
MUTED = "#898781"


def render(store: VectorStore) -> None:
    tab_trace, tab_errors, tab_analytics, tab_data = st.tabs(
        ["🔍 Query Trace", "⚠️ Errors", "📊 Analytics", "🗄️ Stored Data"]
    )

    # ------------------------------------------------------------ Query Trace
    with tab_trace:
        with st.expander("Filters"):
            col1, col2, col3, col4 = st.columns(4)
            date_from = col1.date_input("From", value=None)
            date_to = col2.date_input("To", value=None)
            provider_filter = col3.selectbox("Provider", ["(any)", "groq", "claude"])
            routing_filter = col4.selectbox("Routing path", ["(any)", *CATEGORICAL.keys()])
            errors_only = st.checkbox("Errors only", value=False)

        queries = observability.list_queries(
            date_from=datetime.combine(date_from, datetime.min.time()).isoformat() if date_from else None,
            date_to=datetime.combine(date_to, datetime.max.time()).isoformat() if date_to else None,
            provider=None if provider_filter == "(any)" else provider_filter,
            routing_path=None if routing_filter == "(any)" else routing_filter,
            errors_only=errors_only,
        )

        if not queries:
            st.info("No queries logged yet - ask something in the 🤖 Ask Edukripa widget (bottom right) first.")
        else:
            options = {f"#{q['id']} · {q['question'][:60]} · {q['timestamp'][:19]}": q["id"] for q in queries}
            label = st.selectbox("Query", list(options.keys()))
            query_id = options[label]
            q = observability.get_query(query_id)

            st.subheader("Routing decision")
            path = q["routing_path"] or "none"
            conf, threshold = q["confidence"], q["threshold"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Path taken", path)
            c2.metric("Confidence", f"{conf:.2f}" if conf is not None else "—")
            c3.metric("Threshold", f"{threshold:.2f}" if threshold is not None else "—")
            c4.metric("Auto-gate fired", "Yes" if q["auto_gate_triggered"] else "No")

            if conf is not None and threshold is not None:
                bar_df = pd.DataFrame([
                    {"label": "confidence", "value": conf},
                    {"label": "threshold", "value": threshold},
                ])
                passed = conf >= threshold
                chart = alt.Chart(bar_df).mark_bar(size=28, cornerRadiusEnd=4).encode(
                    x=alt.X("value:Q", scale=alt.Scale(domain=[0, 1]), title=None),
                    y=alt.Y("label:N", title=None, sort=["confidence", "threshold"]),
                    color=alt.Color(
                        "label:N",
                        scale=alt.Scale(
                            domain=["confidence", "threshold"],
                            range=[STATUS_GOOD if passed else STATUS_CRITICAL, MUTED],
                        ),
                        legend=None,
                    ),
                    tooltip=["label", alt.Tooltip("value:Q", format=".2f")],
                ).properties(height=110)
                st.altair_chart(chart, use_container_width=True)

            if q["error"]:
                st.error(f"Query error: {q['error']}")

            sub_retrieval, sub_chunking, sub_llm, sub_web, sub_cost = st.tabs(
                ["Retrieval trace", "Chunking details", "LLM I/O", "Web fallback", "Cost & latency"]
            )

            candidates = observability.get_retrieval_candidates(query_id)

            with sub_retrieval:
                if not candidates:
                    st.write("No retrieval candidates logged for this query.")
                else:
                    df = pd.DataFrame(candidates)
                    df["status"] = df["kept"].map({1: "kept", 0: "discarded"})
                    st.dataframe(
                        df[["iteration", "rank", "source", "page", "chunk_id", "distance", "confidence", "status"]]
                        .sort_values(["iteration", "rank"]),
                        use_container_width=True, hide_index=True,
                    )

            with sub_chunking:
                if not candidates:
                    st.write("Nothing to show.")
                else:
                    for c in candidates:
                        meta = store.get_chunk_metadata(c["source"], c["chunk_id"])
                        tag = "kept" if c["kept"] else "discarded"
                        with st.expander(f"{c['source']} · page {c['page']} · chunk {c['chunk_id']} ({tag})"):
                            if meta:
                                st.write(
                                    f"word range: {meta.get('word_start')}–{meta.get('word_end')} · "
                                    f"chunk_size: {meta.get('chunk_size')} · overlap: {meta.get('overlap')}"
                                )
                                st.text(meta["text"])
                            else:
                                st.write("_Chunk metadata not found - the index may predate this build._")

            llm_calls = observability.get_llm_calls(query_id)

            with sub_llm:
                if not llm_calls:
                    st.write("No LLM calls logged.")
                for call in llm_calls:
                    header = (
                        f"Iteration {call['iteration']} · {call['model']} · "
                        f"{call['input_tokens']}in/{call['output_tokens']}out · {call['latency_ms']:.0f} ms"
                    )
                    with st.expander(header):
                        st.markdown("**Messages sent** (including injected tool-result context):")
                        st.json(call["messages"])
                        st.markdown("**Params:**")
                        st.json(call["params"])
                        st.markdown("**Raw response text:**")
                        st.write(call["response_text"] or "_(tool call - no text in this turn)_")
                        st.caption(f"stop_reason: {call['stop_reason']}")

            tool_calls = observability.get_tool_calls(query_id)
            web_results = observability.get_web_results(query_id)

            with sub_web:
                web_tool_calls = [t for t in tool_calls if t["tool_name"] == "web_search"]
                if not web_tool_calls:
                    st.write("Web search was not triggered for this query.")
                else:
                    for t in web_tool_calls:
                        st.markdown(
                            f"**Searched:** `{t['input_query']}` · triggered by **{t['triggered_by']}** "
                            f"({t['latency_ms']:.0f} ms)"
                        )
                    if web_results:
                        st.dataframe(
                            pd.DataFrame(web_results)[["rank", "title", "url", "snippet"]],
                            use_container_width=True, hide_index=True,
                        )

            with sub_cost:
                c1, c2, c3 = st.columns(3)
                c1.metric("Total latency", f"{q['total_latency_ms']:.0f} ms" if q["total_latency_ms"] is not None else "—")
                c2.metric("Tokens (in/out)", f"{q['total_input_tokens']}/{q['total_output_tokens']}")
                c3.metric("Est. cost", f"${q['estimated_cost_usd']:.4f}" if q["estimated_cost_usd"] is not None else "—")

                stage_rows = [{"stage": f"tool: {t['tool_name']} ({t['triggered_by']})", "ms": t["latency_ms"]} for t in tool_calls]
                stage_rows += [{"stage": f"llm iter {c['iteration']}", "ms": c["latency_ms"]} for c in llm_calls]
                if stage_rows:
                    stage_df = pd.DataFrame(stage_rows)
                    chart = alt.Chart(stage_df).mark_bar(color=SEQUENTIAL_BLUE, cornerRadiusEnd=4).encode(
                        x=alt.X("ms:Q", title="milliseconds"),
                        y=alt.Y("stage:N", sort="-x", title=None),
                        tooltip=["stage", alt.Tooltip("ms:Q", format=".0f")],
                    )
                    st.altair_chart(chart, use_container_width=True)

    # ----------------------------------------------------------------- Errors
    with tab_errors:
        errors = observability.get_errors()
        if not errors:
            st.write("No errors logged.")
        else:
            st.dataframe(
                pd.DataFrame(errors)[["id", "query_id", "stage", "message", "timestamp"]],
                use_container_width=True, hide_index=True,
            )

    # -------------------------------------------------------------- Analytics
    with tab_analytics:
        analytics = observability.get_analytics()

        if analytics["volume_by_day"]:
            st.subheader("Query volume")
            vol_df = pd.DataFrame(analytics["volume_by_day"])
            chart = alt.Chart(vol_df).mark_line(point=True, color=SEQUENTIAL_BLUE, strokeWidth=2).encode(
                x=alt.X("day:T", title=None),
                y=alt.Y("n:Q", title="queries"),
                tooltip=["day", "n"],
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.write("No queries yet.")

        if analytics["by_routing_path"]:
            st.subheader("Answered from")
            rp_df = pd.DataFrame(analytics["by_routing_path"])
            chart = alt.Chart(rp_df).mark_bar(cornerRadiusEnd=4).encode(
                x=alt.X("n:Q", title="queries"),
                y=alt.Y("routing_path:N", title=None, sort="-x"),
                color=alt.Color(
                    "routing_path:N",
                    scale=alt.Scale(domain=list(CATEGORICAL.keys()), range=list(CATEGORICAL.values())),
                    legend=None,
                ),
                tooltip=["routing_path", "n"],
            )
            st.altair_chart(chart, use_container_width=True)

        if analytics["top_terms"]:
            st.subheader("Most frequent query terms")
            terms_df = pd.DataFrame(analytics["top_terms"], columns=["term", "count"])
            chart = alt.Chart(terms_df).mark_bar(color=SEQUENTIAL_BLUE, cornerRadiusEnd=4).encode(
                x=alt.X("count:Q"),
                y=alt.Y("term:N", sort="-x", title=None),
                tooltip=["term", "count"],
            )
            st.altair_chart(chart, use_container_width=True)

    # ----------------------------------------------------------- Stored Data
    with tab_data:
        st.subheader("Indexed documents")
        sources = sorted(store.list_sources())
        st.write(sources or "_None indexed yet._")

        st.subheader("All chunks")
        chunks = store.all_chunks()
        if chunks:
            df = pd.DataFrame(chunks)
            cols = [c for c in ["source", "page", "chunk_id", "word_start", "word_end", "chunk_size", "overlap", "text"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
        else:
            st.write("_No chunks stored yet._")
