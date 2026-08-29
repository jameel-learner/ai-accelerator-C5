"""
Hanafi Faraid Estate Workbook - Streamlit front end.

Run:  streamlit run app.py
"""

import datetime as dt
import json

import altair as alt
import pandas as pd
import streamlit as st

import auth
import engine as E
import store

st.set_page_config(page_title="Faraid Estate Workbook", page_icon="⚖️",
                   layout="wide", initial_sidebar_state="expanded")

ACCENT = "#0f766e"
POS = "#15803d"
NEG = "#b91c1c"

# --------------------------------------------------------------------------
# sign-in gate - never returns for an unauthenticated or unauthorised visitor
# --------------------------------------------------------------------------
USER = auth.login_gate()


# --------------------------------------------------------------------------
# per-user workspace
# --------------------------------------------------------------------------
def load_workspace(user, force=False):
    """
    Bind st.session_state.cfg to THIS user's saved workspace.

    Seeded from the shared baseline on first sign-in.  Re-seeded whenever the
    signed-in identity changes, so one browser session can never leak one
    user's edits into another's workspace.
    """
    if force or "cfg" not in st.session_state or st.session_state.get("cfg_owner") != user["email"]:
        saved = store.load_state(user["email"])
        # a data editor keyed 'ed_*' would otherwise carry one user's unsaved
        # table edits into the next user's workspace
        for k in [k for k in st.session_state if str(k).startswith(("ed_", "hr_", "raw_json"))]:
            del st.session_state[k]
        if saved:
            st.session_state.cfg = saved["config"]
            st.session_state.cfg_source = "your saved workspace"
            st.session_state.cfg_saved_at = saved.get("saved_at", "")
        else:
            st.session_state.cfg = E.load_config()
            st.session_state.cfg_source = "shared baseline (unsaved)"
            st.session_state.cfg_saved_at = ""
        st.session_state.cfg_owner = user["email"]
    return st.session_state.cfg


def save_workspace(user, cfg, note=""):
    payload = store.save_state(user["email"], cfg, name=user.get("name"), note=note)
    st.session_state.cfg_source = "your saved workspace"
    st.session_state.cfg_saved_at = payload["saved_at"]
    return payload


def money(x):
    return E.inr(x)


def money_col(df, cols):
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c].map(E.inr_full)
    return out


def delta_note(v):
    return ("receives from the others" if v > 0
            else "must bring in / refund" if v < 0 else "square")


cfg = load_workspace(USER)
people = E.people_index(cfg)

# --------------------------------------------------------------------------
# sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("⚖️ Faraid Workbook")
    auth.render_user_card(USER)
    st.caption(f'Workspace: **{st.session_state.get("cfg_source", "")}**'
               + (f' · saved {st.session_state["cfg_saved_at"]}'
                  if st.session_state.get("cfg_saved_at") else ""))
    st.divider()

    page = st.radio("Section", [
        "📊 Overview",
        "⚖️ Fara'id shares",
        "🏠 Properties & corpus",
        "📒 Estate ledger",
        "👤 Heir statement",
        "🪙 Gold",
        "🔍 Scope register",
        "⚙️ Settings",
    ], label_visibility="collapsed")

    st.divider()
    st.subheader("Reckoning basis")
    basis_opts = cfg["policy_meta"]["basis"]["options"]
    basis = st.radio(
        "Basis",
        list(basis_opts.keys()),
        index=list(basis_opts.keys()).index(cfg["policy"].get("basis", "timeline")),
        format_func=lambda k: {"timeline": "Timeline (both deaths)",
                               "father_death": "From father's death",
                               "mother_death": "From mother's death"}[k],
        label_visibility="collapsed",
    )
    cfg["policy"]["basis"] = basis
    st.caption(basis_opts[basis])

    as_of = st.date_input("Account up to", value=E.d(cfg["policy"]["as_of"]))
    cfg["policy"]["as_of"] = as_of.isoformat()

    st.divider()
    st.subheader("Fiqh policy switches")
    pm = cfg["policy_meta"]
    cfg["policy"]["charge_occupation_rent"] = st.toggle(
        pm["charge_occupation_rent"]["label"],
        value=cfg["policy"]["charge_occupation_rent"],
        help=pm["charge_occupation_rent"]["default_reason"])
    cfg["policy"]["include_pre_death_flows"] = st.toggle(
        pm["include_pre_death_flows"]["label"],
        value=cfg["policy"]["include_pre_death_flows"],
        help=pm["include_pre_death_flows"]["default_reason"])
    cfg["policy"]["treat_2015_gift_as_advance"] = st.toggle(
        pm["treat_2015_gift_as_advance"]["label"],
        value=cfg["policy"]["treat_2015_gift_as_advance"],
        help=pm["treat_2015_gift_as_advance"]["default_reason"])
    cfg["policy"]["s1_gold_gift_valid"] = st.toggle(
        pm["s1_gold_gift_valid"]["label"],
        value=cfg["policy"]["s1_gold_gift_valid"],
        help=pm["s1_gold_gift_valid"]["default_reason"])
    cfg["policy"]["include_disputed_p6"] = st.toggle(
        "Include the disputed P6 in the corpus",
        value=cfg["policy"]["include_disputed_p6"],
        help="P6 is sub judice. Keep OFF for a distributable-today figure.")
    cfg["policy"]["gold_split_rule"] = st.selectbox(
        pm["gold_split_rule"]["label"],
        ["shariah", "equal_5"],
        index=["shariah", "equal_5"].index(cfg["policy"]["gold_split_rule"]),
        format_func=lambda k: pm["gold_split_rule"]["options"][k])
    cfg["policy"]["expenses_are_reimbursable"] = st.toggle(
        "Expenses on the estate are reimbursable",
        value=cfg["policy"]["expenses_are_reimbursable"],
        help="A co-owner who preserves the common property may recover the others' rateable share.")
    cfg["policy"]["allow_assumed_streams"] = st.toggle(
        "Include streams marked ASSUMED",
        value=cfg["policy"]["allow_assumed_streams"],
        help="Some flows (e.g. who took the tower rent before the mother's death) are inferred, not stated.")

    st.divider()
    st.subheader("My workspace")
    if st.button("💾 Save my settings", width="stretch", type="primary"):
        save_workspace(USER, cfg, note="saved from the sidebar")
        st.success("Saved to your workspace.")
        st.rerun()
    if st.button("↺ Revert to my last save", width="stretch"):
        if store.load_state(USER["email"]):
            load_workspace(USER, force=True)
            st.rerun()
        else:
            st.warning("You have no saved workspace yet.")
    if st.button("⟲ Reset to shared baseline", width="stretch",
                 help="Discards your unsaved changes and reloads the shared config.json. "
                      "Your saved workspace is untouched until you press Save."):
        st.session_state.cfg = E.load_config()
        st.session_state.cfg_source = "shared baseline (unsaved)"
        st.session_state.cfg_saved_at = ""
        st.rerun()
    st.caption("Your settings are saved under your own name. "
               "Other heirs see their own.")

    st.divider()
    if st.button("👥 Switch user", width="stretch",
                 help="Unsaved changes are discarded. Save first to keep them."):
        auth.switch_user()
        st.rerun()

# --------------------------------------------------------------------------
# compute once
# --------------------------------------------------------------------------
S = E.settlement(cfg, as_of=cfg["policy"]["as_of"], basis=basis)
sh = S["shares"]
val = S["valuation"]
flows = S["flows"]
tbl = S["table"]
heirs = E.heir_ids(cfg)


# ==========================================================================
# 1. OVERVIEW
# ==========================================================================
if page == "📊 Overview":
    st.title("Estate at a glance")
    st.caption(f'Basis: **{basis}** · accounted to **{S["as_of"]}** · '
               f'{"P6 included" if cfg["policy"]["include_disputed_p6"] else "P6 (sub judice) excluded"} · '
               f'{"notional rent ON" if cfg["policy"]["charge_occupation_rent"] else "notional rent OFF"}')

    c = st.columns(4)
    c[0].metric("Gross corpus", money(val["gross_corpus"]))
    c[1].metric("Liabilities (dayn)", money(val["total_liabilities"]),
                help="Refundable tenant advances + funeral + debts + wasiyya")
    c[2].metric("Net distributable", money(val["net_corpus"]))
    c[3].metric("Post-death income accounted", money(flows["totals"]["income_in_scope"]))

    c = st.columns(4)
    c[0].metric("Estate expenses (reimbursable)", money(flows["totals"]["expense_in_scope"]))
    c[1].metric("Net estate income", money(flows["totals"]["net_estate_income"]))
    c[2].metric("Excluded as out-of-scope", money(flows["totals"]["out_of_scope"]),
                help="Lifetime flows and any switched-off notional rent")
    c[3].metric("Gold pool", money(S["gold"]["pool_value"]),
                help=f'{S["gold"]["pool_grams"]:.0f} g @ Rs {S["gold"]["rate"]:,.0f}/g')

    st.divider()
    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("Corpus by property")
        pv = val["properties"].copy()
        pv["label"] = pv["id"] + " " + pv["name"]
        ch = (alt.Chart(pv[pv["estate_value"] > 0])
              .mark_bar(cornerRadius=3, color=ACCENT)
              .encode(
                  x=alt.X("estate_value:Q", title="Estate value (Rs)",
                          axis=alt.Axis(format="~s")),
                  y=alt.Y("label:N", sort="-x", title=None),
                  tooltip=[alt.Tooltip("label:N", title="Property"),
                           alt.Tooltip("estate_value:Q", title="Estate value", format=",.0f"),
                           alt.Tooltip("ownership_share:Q", title="Our share")])
              .properties(height=240))
        st.altair_chart(ch, width="stretch")

        top = pv.loc[pv["estate_value"].idxmax()]
        st.info(f'**Concentration risk** — {top["id"]} {top["name"]} alone is '
                f'{top["estate_value"]/val["gross_corpus"]*100:.1f}% of the corpus. '
                "No equitable partition is possible without either selling it or "
                "loading the other five properties heavily against it.")

    with right:
        st.subheader("Entitlement by heir")
        t = tbl.copy()
        ch = (alt.Chart(t).mark_arc(innerRadius=55, stroke="#fff", strokeWidth=2)
              .encode(
                  theta=alt.Theta("total_entitlement:Q"),
                  color=alt.Color("name:N", title=None,
                                  scale=alt.Scale(scheme="teals")),
                  tooltip=[alt.Tooltip("name:N", title="Heir"),
                           alt.Tooltip("share_fraction:N", title="Qur'anic share"),
                           alt.Tooltip("total_entitlement:Q", title="Total", format=",.0f")])
              .properties(height=240))
        st.altair_chart(ch, width="stretch")

        sons = t[t["relation"] == "son"]["total_entitlement"].sum()
        daus = t[t["relation"] == "daughter"]["total_entitlement"].sum()
        st.caption(f"Sons (2 heads): {money(sons)}  ·  Daughters (3 heads): {money(daus)}")

    st.divider()
    st.subheader("Where each heir stands today")
    disp = tbl[["name", "relation", "share_fraction", "share_pct",
                "corpus_entitlement", "income_expense_net", "gold_adjustment",
                "gift_setoff", "total_entitlement"]].copy()
    disp.columns = ["Heir", "Class", "Share", "Share %", "Corpus entitlement",
                    "Rent/expense net", "Gold adjustment", "Gift set-off", "Total entitlement"]
    st.dataframe(
        disp, hide_index=True, width="stretch",
        column_config={
            "Share %": st.column_config.NumberColumn(format="%.2f%%"),
            "Corpus entitlement": st.column_config.NumberColumn(format="₹%,.0f"),
            "Rent/expense net": st.column_config.NumberColumn(format="₹%,.0f"),
            "Gold adjustment": st.column_config.NumberColumn(format="₹%,.0f"),
            "Gift set-off": st.column_config.NumberColumn(format="₹%,.0f"),
            "Total entitlement": st.column_config.NumberColumn(format="₹%,.0f"),
        })

    st.subheader("Cash to settle between the heirs (before the corpus is divided)")
    net = flows["positions"][flows["positions"]["net"].abs() > 1].copy()
    if len(net):
        net["dir"] = net["net"].map(lambda v: "receivable" if v > 0 else "payable")
        ch = (alt.Chart(net).mark_bar(cornerRadius=3)
              .encode(
                  x=alt.X("net:Q", title="Net position (Rs)", axis=alt.Axis(format="~s")),
                  y=alt.Y("name:N", sort="-x", title=None),
                  color=alt.Color("dir:N", title=None,
                                  scale=alt.Scale(domain=["receivable", "payable"],
                                                  range=[POS, NEG])),
                  tooltip=[alt.Tooltip("name:N"), alt.Tooltip("net:Q", format=",.0f")])
              .properties(height=200))
        st.altair_chart(ch, width="stretch")
        st.caption("Positive = collected less than entitled / spent more than liable, so this "
                   "heir is owed. Negative = over-collected, so this heir brings money in.")
    if abs(S["mother_net_rolled"]) > 1:
        st.warning(f'The mother\'s own flow position of {money(S["mother_net_rolled"])} was '
                   "not settled in her lifetime, so it rolls into her tarikah (munasakha) and "
                   "has been re-split 2:1 among the five children in the table above.")

    st.divider()
    st.caption("⚠️ " + cfg["meta"]["disclaimer"])


# ==========================================================================
# 2. FARA'ID SHARES
# ==========================================================================
elif page == "⚖️ Fara'id shares":
    st.title("Fara'id computation")
    st.caption("Two successive deaths, so two successive distributions (munasakha).")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Stage 1 — Hanif, d. 20 Jul 2022")
        st.caption("Heirs: widow + 2 sons + 3 daughters. Base of 8, then 7 residuary units → **56**.")
        rows = []
        for pid, fr in sh["ef"].items():
            rows.append({"Heir": people[pid]["name"], "Class": people[pid]["relation"],
                         "Share": str(fr), "of 56": int(fr * 56),
                         "%": float(fr) * 100,
                         "Value": val["net_corpus"] * float(fr)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={"%": st.column_config.NumberColumn(format="%.3f%%"),
                                    "Value": st.column_config.NumberColumn(format="₹%,.0f")})
        for n in sh["notes_father"]:
            st.caption("• " + n)

    with c2:
        st.subheader("Stage 2 — Khudsia, d. 28 Oct 2025")
        st.caption("Heirs: 2 sons + 3 daughters. No spouse, no fixed sharer → the whole "
                   "estate goes to the children as 'asaba, base **7**.")
        rows = []
        her_corpus = val["net_corpus"] * float(sh["widow_share"])
        for pid, fr in sh["em"].items():
            rows.append({"Heir": people[pid]["name"], "Class": people[pid]["relation"],
                         "Share": str(fr), "of 7": int(fr * 7),
                         "%": float(fr) * 100,
                         "Value from her 1/8": her_corpus * float(fr)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={"%": st.column_config.NumberColumn(format="%.3f%%"),
                                    "Value from her 1/8": st.column_config.NumberColumn(format="₹%,.0f")})
        for n in sh["notes_mother"]:
            st.caption("• " + n)
        st.caption(f'Her 1/8 of the father\'s corpus = {money(her_corpus)}, plus her own gold.')

    st.divider()
    st.subheader("Consolidated entitlement in the father's corpus")
    rows = []
    for pid, fr in sh["final"].items():
        rows.append({
            "Heir": people[pid]["name"], "Class": people[pid]["relation"],
            "From father": str(sh["ef"][pid]),
            "Via mother": str(sh["widow_share"] * sh["em"][pid]),
            "Combined": str(fr), "of 56": int(fr * 56), "%": float(fr) * 100,
            "Value": val["net_corpus"] * float(fr)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={"%": st.column_config.NumberColumn(format="%.3f%%"),
                                "Value": st.column_config.NumberColumn(format="₹%,.0f")})

    st.success(
        "**The arithmetic closes on itself.** 1/4 + (1/8 × 2/7) = 2/7 for each son and "
        "1/8 + (1/8 × 1/7) = 1/7 for each daughter. Because the widow's 1/8 flows back to "
        "the same five children in the same 2:1 proportion, the consolidated split is "
        "identical to a single-stage 2:1 division. The two stages still have to be run "
        "separately for the **income** between 20 Jul 2022 and 28 Oct 2025, where the "
        "mother was a live 1/8 stakeholder — and they would matter enormously if any heir "
        "had died, disclaimed, or settled in that window.")

    st.divider()
    st.subheader("Sensitivity: what changes the shares")
    st.markdown("""
| If this were true | Effect |
|---|---|
| The father had left a surviving parent | Mother/father of the deceased takes 1/6 each, cutting the children's residue |
| The mother had predeceased the father | No 1/8 widow share at all; the children take the whole estate 2:1 directly |
| A valid wasiyya to a non-heir existed | Up to 1/3 comes off the top **before** any share is computed |
| A bequest were made in favour of one child | Void in Hanafi law unless **every** other adult heir consents after the death |
| An unpaid mahr were proved | It is a **debt** of the father's estate to the widow, paid before shares, and it swells her 1/8 base |
| An heir renounced (takharuj) | Valid only for consideration and by agreement; it is a sale of a share, not a fara'id event |
""")


# ==========================================================================
# 3. PROPERTIES
# ==========================================================================
elif page == "🏠 Properties & corpus":
    st.title("Properties & corpus")

    pv = val["properties"].copy()
    pv["share_of_corpus"] = pv["estate_value"] / max(val["gross_corpus"], 1) * 100
    disp = pv[["id", "name", "kind", "area_sqft", "gross_value", "ownership_share",
               "estate_value", "share_of_corpus", "disputed", "note"]]
    disp.columns = ["ID", "Property", "Type", "Area (sqft)", "Gross value",
                    "Our share", "Estate value", "% of corpus", "Disputed", "Note"]
    st.dataframe(disp, hide_index=True, width="stretch",
                 column_config={
                     "Gross value": st.column_config.NumberColumn(format="₹%,.0f"),
                     "Estate value": st.column_config.NumberColumn(format="₹%,.0f"),
                     "Our share": st.column_config.NumberColumn(format="%.0f%%"),
                     "% of corpus": st.column_config.NumberColumn(format="%.1f%%"),
                 })

    c = st.columns(3)
    c[0].metric("Gross corpus", money(val["gross_corpus"]))
    c[1].metric("Tenant advances (refundable)", money(val["tenant_advances"]))
    c[2].metric("Net distributable", money(val["net_corpus"]))

    st.subheader("Liabilities charged before the shares")
    st.caption("Hanafi order of payment: funeral → debts → wasiyya (max 1/3) → fara'id shares.")
    st.dataframe(val["liabilities"], hide_index=True, width="stretch",
                 column_config={"amount": st.column_config.NumberColumn("Amount", format="₹%,.0f")})

    st.divider()
    st.subheader("Rent roll — every estate-owned unit")
    ru = pd.DataFrame(cfg["rent_units"])
    ru["annual_rent"] = ru["rent"].astype(float) * 12
    ru["status"] = ru.apply(
        lambda r: "Estate — let" if r["estate_owned"] and r["occupant"] == "tenant"
        else "Estate — occupied by heir" if r["estate_owned"]
        else "Sold to outsider", axis=1)
    st.dataframe(
        ru[["property", "unit", "floor", "bhk", "status", "occupant", "collector",
            "rent", "annual_rent", "advance"]],
        hide_index=True, width="stretch",
        column_config={
            "rent": st.column_config.NumberColumn("Monthly rent", format="₹%,.0f"),
            "annual_rent": st.column_config.NumberColumn("Annualised", format="₹%,.0f"),
            "advance": st.column_config.NumberColumn("Deposit held", format="₹%,.0f"),
        })

    est = ru[ru["estate_owned"]].copy()
    est["rent"] = est["rent"].astype(float)
    cash = est[est["occupant"] == "tenant"]           # actually produces money
    imputed = est[est["occupant"] != "tenant"]        # occupied by an heir

    # cash rent actually reaching the estate, from every property
    p2_cash = float(cash.loc[cash["property"] == "P2", "rent"].sum())
    farm_annual = sum(float(s_["amount"]) for s_ in cfg["streams"]
                      if s_["kind"] == "rent" and s_["property"] == "P5"
                      and s_.get("period") == "annual")
    cash_annual = float(cash["rent"].sum()) * 12 + farm_annual
    p2_value = float(pv.loc[pv["id"] == "P2", "estate_value"].iloc[0])

    c = st.columns(4)
    c[0].metric("Estate-owned units", len(est),
                f'{len(cash)} let · {len(imputed)} occupied by an heir')
    c[1].metric("Cash rent / month (all let units)", money(cash["rent"].sum()))
    c[2].metric("Imputed rent forgone / month", money(imputed["rent"].sum()),
                help="Market rent of the units occupied by B1 and B2. Not charged unless "
                     "the notional-rent switch is on.")
    c[3].metric("P2 gross yield", f'{p2_cash * 12 / max(p2_value, 1) * 100:.2f}%',
                help="P2 cash rent only, against P2's own estate value.")

    st.info("**Sale-vs-hold.** Cash rent across the whole estate annualises to about "
            f'{money(cash_annual)} against a corpus of {money(val["gross_corpus"])} — roughly '
            f'{cash_annual / max(val["gross_corpus"], 1) * 100:.2f}% gross, before tax, '
            "maintenance and vacancy. P1 and P4 are bare land and yield nothing at all, yet "
            f'they are {(float(pv.loc[pv["id"].isin(["P1","P4"]), "estate_value"].sum()) / max(val["gross_corpus"],1) * 100):.0f}% '
            "of the value. Holding jointly earns the family well under a fixed-deposit "
            "return while generating the very rent disputes this workbook exists to settle; "
            "that asymmetry is the strongest financial argument for selling and distributing.")


# ==========================================================================
# 4. LEDGER
# ==========================================================================
elif page == "📒 Estate ledger":
    st.title("Estate income & expense ledger")
    st.caption("Every stream is cut at each death date; each segment is allocated on the "
               "ownership map that was actually in force during it.")

    led = flows["ledger"].copy()
    if not len(led):
        st.warning("No streams configured.")
        st.stop()

    c = st.columns(4)
    ins = led[led["in_scope"]]
    c[0].metric("In-scope income", money(ins.loc[ins["kind"].isin(["rent", "notional_rent"]), "amount"].sum()))
    c[1].metric("In-scope expenses", money(ins.loc[ins["kind"] == "expense", "amount"].sum()))
    c[2].metric("Out-of-scope", money(led.loc[~led["in_scope"], "amount"].sum()))
    c[3].metric("Segments", len(led))

    st.subheader("Accrual by window")
    w = (led.groupby(["window", "kind", "in_scope"])["amount"].sum().reset_index())
    ch = (alt.Chart(w).mark_bar(cornerRadius=3)
          .encode(
              x=alt.X("amount:Q", title="Rs", axis=alt.Axis(format="~s")),
              y=alt.Y("window:N", title=None, sort=None),
              color=alt.Color("kind:N", title="Kind", scale=alt.Scale(scheme="tableau10")),
              opacity=alt.Opacity("in_scope:N", title="Counted",
                                  scale=alt.Scale(domain=[True, False], range=[1.0, 0.28])),
              tooltip=["window", "kind", "in_scope",
                       alt.Tooltip("amount:Q", format=",.0f")])
          .properties(height=190))
    st.altair_chart(ch, width="stretch")

    st.subheader("Who collected what, by window")
    piv = (ins[ins["kind"].isin(["rent", "notional_rent"])]
           .pivot_table(index="actor", columns="window", values="amount",
                        aggfunc="sum", fill_value=0.0))
    piv["TOTAL"] = piv.sum(axis=1)
    piv.index = [people[i]["name"] if i in people else i for i in piv.index]
    st.dataframe(piv.round(0), width="stretch")

    st.subheader("Who paid what, by category")
    ex = ins[ins["kind"] == "expense"]
    if len(ex):
        pex = ex.pivot_table(index="actor", columns="category", values="amount",
                             aggfunc="sum", fill_value=0.0)
        pex["TOTAL"] = pex.sum(axis=1)
        pex.index = [people[i]["name"] if i in people else i for i in pex.index]
        st.dataframe(pex.round(0), width="stretch")

    st.divider()
    st.subheader("Segment detail")
    show_out = st.checkbox("Show out-of-scope segments too", value=True)
    view = led if show_out else ins
    v = view[["stream_id", "kind", "property", "unit", "actor", "window",
              "seg_start", "seg_end", "months", "rate", "amount", "in_scope",
              "assumed", "excl_reason", "note"]].copy()
    v["actor"] = v["actor"].map(lambda i: people[i]["name"] if i in people else i)
    st.dataframe(v.sort_values(["window", "kind", "actor"]), hide_index=True,
                 width="stretch",
                 column_config={
                     "months": st.column_config.NumberColumn(format="%.1f"),
                     "rate": st.column_config.NumberColumn(format="₹%,.0f"),
                     "amount": st.column_config.NumberColumn(format="₹%,.0f"),
                     "excl_reason": st.column_config.TextColumn("Why excluded", width="large"),
                 })

    if led["assumed"].any():
        st.warning("Rows flagged **assumed** are inferences, not stated facts — chiefly who "
                   "took the Jio tower rent before the mother's death. Verify before relying "
                   "on the numbers, or switch assumed streams off in the sidebar.")


# ==========================================================================
# 5. HEIR STATEMENT
# ==========================================================================
elif page == "👤 Heir statement":
    st.title("Individual heir statement")
    mine = auth.heir_for(USER["email"], cfg)
    default_ix = heirs.index(mine) if mine in heirs else 0
    who = st.selectbox("Heir", heirs, index=default_ix,
                       format_func=lambda p: f'{people[p]["name"]} — {people[p]["relation"]}'
                                             + ("  (you)" if p == mine else ""))
    if mine and who == mine:
        st.caption("This is your own statement — it opened here because you are signed in "
                   "as this heir.")
    row = tbl[tbl["person"] == who].iloc[0]
    pos = flows["positions"]
    prow = pos[pos["person"] == who]
    prow = prow.iloc[0] if len(prow) else None

    st.header(f'{people[who]["name"]}  ·  {people[who]["relation"]}')

    c = st.columns(4)
    c[0].metric("Qur'anic share", row["share_fraction"], f'{row["share_pct"]:.2f}%')
    c[1].metric("Corpus entitlement", money(row["corpus_entitlement"]))
    c[2].metric("Rent / expense net", money(row["income_expense_net"]),
                delta_note(row["income_expense_net"]))
    c[3].metric("Total entitlement", money(row["total_entitlement"]))

    st.divider()
    l, r = st.columns(2)

    with l:
        st.subheader("Flow account")
        if prow is not None:
            fa = pd.DataFrame([
                {"Item": "Rent this heir was entitled to", "Amount": prow["entitled"]},
                {"Item": "Rent this heir actually collected", "Amount": -prow["received"]},
                {"Item": "Estate expenses this heir paid", "Amount": prow["paid"]},
                {"Item": "This heir's rateable share of estate expenses", "Amount": -prow["liable"]},
                {"Item": "NET", "Amount": prow["net"]},
            ])
            st.dataframe(fa, hide_index=True, width="stretch",
                         column_config={"Amount": st.column_config.NumberColumn(format="₹%,.0f")})
            st.caption("Positive lines are credits to this heir; negative lines are charges.")

        st.subheader("Gold")
        g = S["gold"]["table"]
        grow = g[g["person"] == who]
        if len(grow):
            grow = grow.iloc[0]
            st.write(f'Entitled **{grow["entitled_g"]:.2f} g** ({grow["rule"]}), '
                     f'actually took **{grow["actually_taken_g"]:.2f} g** → '
                     f'**{grow["delta_g"]:+.2f} g** ({money(grow["delta_value"])}).')

    with r:
        st.subheader("Property in this heir's hands")
        occ = [u for u in cfg["rent_units"] if u.get("occupant") == who]
        if occ:
            for u in occ:
                notional = float(u["rent"]) if cfg["policy"]["charge_occupation_rent"] else 0.0
                st.write(f'• **{u["property"]} / {u["unit"]}** ({u["bhk"]}) — in personal occupation. '
                         f'Market rent {E.inr_full(u["rent"])}/mo; '
                         + (f'charged as notional rent.' if notional
                            else 'not charged (Hanafi default — no ujrat al-mithl between co-owners).'))
        else:
            st.write("• None in personal occupation.")

        coll = sorted({s["unit"] for s in cfg["streams"]
                       if s["actor"] == who and s["kind"] == "rent"})
        st.write("**Units whose rent this heir collects:** " + (", ".join(coll) if coll else "none"))

        st.subheader("Undivided ownership today")
        st.write(f'This heir owns an undivided **{row["share_fraction"]}** '
                 f'({row["share_pct"]:.2f}%) of every unpartitioned estate asset — '
                 "a musha' share, not any identified flat or plot. No heir may sell, "
                 "let, or build on a specific item without partition or the others' consent.")
        pv = val["properties"]
        pp = pv[pv["estate_value"] > 0][["id", "name", "estate_value"]].copy()
        pp["This heir's slice"] = pp["estate_value"] * row["share_pct"] / 100
        st.dataframe(pp, hide_index=True, width="stretch",
                     column_config={
                         "estate_value": st.column_config.NumberColumn("Estate value", format="₹%,.0f"),
                         "This heir's slice": st.column_config.NumberColumn(format="₹%,.0f")})

    st.divider()
    st.subheader("Line-by-line allocation")
    al = flows["alloc"]
    a = al[al["person"] == who].copy()
    if len(a):
        a["actor"] = a["actor"].map(lambda i: people[i]["name"] if i in people else i)
        st.dataframe(
            a[["stream_id", "kind", "property", "unit", "window", "actor", "share",
               "entitled", "received", "paid", "liable", "net"]],
            hide_index=True, width="stretch",
            column_config={
                "share": st.column_config.NumberColumn(format="%.4f"),
                "entitled": st.column_config.NumberColumn(format="₹%,.0f"),
                "received": st.column_config.NumberColumn(format="₹%,.0f"),
                "paid": st.column_config.NumberColumn(format="₹%,.0f"),
                "liable": st.column_config.NumberColumn(format="₹%,.0f"),
                "net": st.column_config.NumberColumn(format="₹%,.0f"),
            })


# ==========================================================================
# 6. GOLD
# ==========================================================================
elif page == "🪙 Gold":
    st.title("Gold jewellery — the mother's movable estate")
    g = S["gold"]

    c = st.columns(4)
    c[0].metric("Total left", f'{cfg["gold"]["total_grams"]:.0f} g')
    c[1].metric("Treated as gifted away", f'{g["gifted_grams"]:.0f} g')
    c[2].metric("Divisible pool", f'{g["pool_grams"]:.0f} g', money(g["pool_value"]))
    c[3].metric("Rule applied", cfg["policy"]["gold_split_rule"])

    st.dataframe(
        g["table"], hide_index=True, width="stretch",
        column_config={
            "entitled_g": st.column_config.NumberColumn("Entitled (g)", format="%.2f"),
            "actually_taken_g": st.column_config.NumberColumn("Actually took (g)", format="%.2f"),
            "delta_g": st.column_config.NumberColumn("Difference (g)", format="%+.2f"),
            "delta_value": st.column_config.NumberColumn("Difference (Rs)", format="₹%,.0f"),
        })

    ch = (alt.Chart(g["table"].melt(id_vars=["name"],
                                    value_vars=["entitled_g", "actually_taken_g"],
                                    var_name="basis", value_name="grams"))
          .mark_bar(cornerRadius=3)
          .encode(x=alt.X("name:N", title=None),
                  xOffset="basis:N",
                  y=alt.Y("grams:Q", title="Grams"),
                  color=alt.Color("basis:N", title=None,
                                  scale=alt.Scale(domain=["entitled_g", "actually_taken_g"],
                                                  range=[ACCENT, "#f59e0b"])),
                  tooltip=["name", "basis", alt.Tooltip("grams:Q", format=".2f")])
          .properties(height=260))
    st.altair_chart(ch, width="stretch")

    st.subheader("The two live issues")
    st.error(f'**1. S1\'s 30 g bangles.** {g["note"]}')
    st.warning(f'**2. The equal five-way split.** {g["split_note"]}')
    st.info("Note the interaction: the equal split already over-pays the three daughters "
            "and under-pays the two sons relative to 2:1. Layering a disputed 30 g gift on "
            "top of an already non-shar'i division is why this item is generating heat out "
            "of all proportion to its value — it is under 1% of the estate.")


# ==========================================================================
# 7. SCOPE REGISTER
# ==========================================================================
elif page == "🔍 Scope register":
    st.title("What the fara'id touches — and what it does not")
    st.caption("The single most important step. Anything done by an owner while alive is his "
               "own affair; the tarikah opens only at the instant of death.")

    reg = E.scope_register(cfg, as_of=cfg["policy"]["as_of"], basis=basis)

    counts = reg.groupby("scope").size().reset_index(name="rows")
    c = st.columns(len(counts))
    for i, r in counts.iterrows():
        c[i].metric(r["scope"], int(r["rows"]))

    pick = st.multiselect("Filter", sorted(reg["scope"].unique()),
                          default=sorted(reg["scope"].unique()))
    show = reg[reg["scope"].isin(pick)]

    for scope in ["OUT", "SUSPENDED", "PARTIAL", "IN"]:
        sub = show[show["scope"] == scope]
        if not len(sub):
            continue
        title = {"OUT": "🚫 OUTSIDE the fara'id",
                 "SUSPENDED": "⏸️ SUSPENDED (mawquf)",
                 "PARTIAL": "◐ PARTIALLY estate property",
                 "IN": "✅ INSIDE the fara'id"}[scope]
        st.subheader(title)
        st.dataframe(
            sub[["ref", "when", "what", "actor", "amount", "bucket", "reason"]],
            hide_index=True, width="stretch",
            column_config={
                "amount": st.column_config.NumberColumn("Amount", format="₹%,.0f"),
                "reason": st.column_config.TextColumn("Fiqh reasoning", width="large"),
            })


# ==========================================================================
# 8. SETTINGS
# ==========================================================================
elif page == "⚙️ Settings":
    st.title("Settings — edit the underlying data")
    st.caption("Everything the app computes comes from your workspace configuration. "
               "Edit here, press the section's Apply button, then **Save my settings** — "
               "changes are stored under your own name, not shared with the others.")

    tabs = st.tabs(["My workspace", "People & estates", "Properties", "Rent units",
                    "Streams", "Liabilities", "Gold", "Lifetime acts", "Raw JSON"])

    with tabs[0]:
        st.subheader("My saved workspace")
        saved = store.load_state(USER["email"])
        c = st.columns(3)
        c[0].metric("Signed in as", USER["name"], USER["email"])
        c[1].metric("Workspace", "saved" if saved else "not saved yet",
                    saved.get("saved_at", "") if saved else "using shared baseline")
        c[2].metric("Revisions kept", len(store.list_revisions(USER["email"])))

        note = st.text_input("Label this save (optional)", "",
                             placeholder="e.g. with notional rent charged")
        cc = st.columns(3)
        if cc[0].button("💾 Save my settings", type="primary", key="ws_save"):
            save_workspace(USER, cfg, note=note)
            st.success("Saved to your workspace.")
            st.rerun()
        if cc[1].button("↺ Revert to my last save", key="ws_revert"):
            if saved:
                load_workspace(USER, force=True)
                st.rerun()
            else:
                st.warning("Nothing saved yet.")
        if cc[2].button("⟲ Reset to shared baseline", key="ws_reset"):
            st.session_state.cfg = E.load_config()
            st.session_state.cfg_source = "shared baseline (unsaved)"
            st.session_state.cfg_saved_at = ""
            st.rerun()

        st.download_button(
            "⬇️ Download my workspace",
            json.dumps({"email": USER["email"], "config": cfg}, indent=2, ensure_ascii=False),
            file_name=f'faraid-workspace-{store.user_key(USER["email"])}.json',
            mime="application/json", key="ws_dl")

        up = st.file_uploader("Restore a workspace file", type=["json"], key="ws_up")
        if up is not None:
            try:
                payload = json.load(up)
                restored = payload.get("config", payload)
                if not isinstance(restored, dict) or "policy" not in restored:
                    st.error("That file does not look like a workspace or a config.")
                else:
                    st.session_state.cfg = restored
                    st.session_state.cfg_source = "restored from file (unsaved)"
                    st.success("Loaded. Press Save my settings to keep it.")
                    st.rerun()
            except json.JSONDecodeError as ex:
                st.error(f"Invalid JSON: {ex}")

        st.divider()
        st.subheader("Revision history")
        revs = store.list_revisions(USER["email"])
        if not revs:
            st.caption("No revisions yet — one is kept automatically each time you save over "
                       "an existing workspace.")
        else:
            for r in revs[:12]:
                rc = st.columns([3, 4, 1.4])
                rc[0].write(f'`{r["saved_at"] or r["file"]}`')
                rc[1].caption(r["note"] or "—")
                if rc[2].button("Restore", key=f'rest_{r["file"]}'):
                    payload = store.load_revision(r["path"])
                    if payload:
                        st.session_state.cfg = payload["config"]
                        st.session_state.cfg_source = "restored revision (unsaved)"
                        st.success("Loaded that revision. Press Save my settings to keep it.")
                        st.rerun()
                    else:
                        st.error("That revision could not be read.")

        st.divider()
        st.subheader("Danger zone")
        if st.checkbox("I want to delete my saved workspace", key="ws_del_ok"):
            if st.button("Delete my workspace", key="ws_del"):
                store.delete_state(USER["email"])
                st.session_state.cfg = E.load_config()
                st.session_state.cfg_source = "shared baseline (unsaved)"
                st.session_state.cfg_saved_at = ""
                st.success("Deleted. A revision snapshot was kept.")
                st.rerun()

        if USER.get("is_admin"):
            st.divider()
            st.subheader("Admin")
            st.caption("The shared baseline seeds every new user and supplies the sign-in "
                       "allow-list. Changing it does not touch anyone's saved workspace.")
            everyone = store.list_states()
            if everyone:
                st.dataframe(pd.DataFrame(everyone), hide_index=True, width="stretch")
            else:
                st.caption("No user workspaces saved yet.")
            if st.checkbox("Publish my current configuration as the shared baseline",
                           key="adm_ok"):
                if st.button("Overwrite config.json", key="adm_pub"):
                    E.save_config(cfg)
                    st.success(f"Shared baseline updated at {E.CONFIG_PATH}")

    with tabs[1]:
        st.subheader("People")
        st.caption("The **email** column records which of the five fixed users each heir is. "
                   "The authoritative list lives in `auth.py` (USERS); this column is a "
                   "readable mirror of it and a fallback if the users are renamed.")
        pdf = st.data_editor(pd.DataFrame(cfg["people"]), num_rows="dynamic",
                             width="stretch", key="ed_people")
        if st.button("Apply people", key="ap_people"):
            cfg["people"] = pdf.where(pd.notna(pdf), None).to_dict("records")
            st.success("Applied to session.")
        st.subheader("Estates & heir classes")
        for e in cfg["estates"]:
            with st.expander(f'{e["id"]} — {e["label"]}', expanded=False):
                e["death_date"] = st.text_input("Death date (YYYY-MM-DD)", e["death_date"],
                                                key=f'dd_{e["id"]}')
                hdf = st.data_editor(pd.DataFrame(e["heirs"]), num_rows="dynamic",
                                     width="stretch", key=f'hr_{e["id"]}',
                                     column_config={"group": st.column_config.SelectboxColumn(
                                         options=["husband", "wife", "father", "mother",
                                                  "son", "daughter"])})
                if st.button("Apply heirs", key=f'ah_{e["id"]}'):
                    e["heirs"] = hdf.to_dict("records")
                    st.success("Applied.")
                st.caption(e.get("note", ""))

    with tabs[2]:
        st.subheader("Properties")
        st.caption("Set `rate_per_sqft` to value by rate (P1), otherwise `lump_value` is used. "
                   "`ownership_share` carves out a partner's stake.")
        df = st.data_editor(pd.DataFrame(cfg["properties"]), num_rows="dynamic",
                            width="stretch", key="ed_prop")
        if st.button("Apply properties", key="ap_prop"):
            cfg["properties"] = df.where(pd.notna(df), None).to_dict("records")
            st.success("Applied.")

    with tabs[3]:
        st.subheader("Rent units")
        df = st.data_editor(pd.DataFrame(cfg["rent_units"]), num_rows="dynamic",
                            width="stretch", key="ed_units")
        if st.button("Apply rent units", key="ap_units"):
            cfg["rent_units"] = df.where(pd.notna(df), None).to_dict("records")
            st.success("Applied.")

    with tabs[4]:
        st.subheader("Income & expense streams")
        st.caption("`kind`: rent | notional_rent | expense.  `period`: monthly | annual | oneoff.  "
                   "Blank `end` means 'still running'. Add a row to record any new event.")
        df = st.data_editor(
            pd.DataFrame(cfg["streams"]), num_rows="dynamic", width="stretch", key="ed_str",
            column_config={
                "kind": st.column_config.SelectboxColumn(options=["rent", "notional_rent", "expense"]),
                "period": st.column_config.SelectboxColumn(options=["monthly", "annual", "oneoff"]),
                "actor": st.column_config.SelectboxColumn(options=[p["id"] for p in cfg["people"]]),
            })
        if st.button("Apply streams", key="ap_str"):
            cfg["streams"] = df.where(pd.notna(df), None).to_dict("records")
            st.success("Applied.")

    with tabs[5]:
        st.subheader("Estate liabilities")
        st.caption("Use the literal string `AUTO_ADVANCES` to have tenant deposits summed "
                   "automatically. Add funeral costs, proven debts, unpaid mahr, and any "
                   "wasiyya here — they all come off before the shares.")
        df = st.data_editor(pd.DataFrame(cfg["estate_liabilities"]), num_rows="dynamic",
                            width="stretch", key="ed_liab")
        if st.button("Apply liabilities", key="ap_liab"):
            cfg["estate_liabilities"] = df.where(pd.notna(df), None).to_dict("records")
            st.success("Applied.")

    with tabs[6]:
        st.subheader("Gold")
        g = cfg["gold"]
        c = st.columns(3)
        g["total_grams"] = c[0].number_input("Total grams", value=float(g["total_grams"]), step=1.0)
        g["s1_claim_grams"] = c[1].number_input("S1 claimed grams", value=float(g["s1_claim_grams"]), step=1.0)
        g["rate_per_gram"] = c[2].number_input("Rate per gram (Rs)", value=float(g["rate_per_gram"]), step=100.0)
        g["s1_claim_note"] = st.text_area("Note on the claim", g["s1_claim_note"], height=140)
        g["actual_split_note"] = st.text_area("Note on the split actually done",
                                              g["actual_split_note"], height=120)

    with tabs[7]:
        st.subheader("Lifetime acts (the out-of-scope register)")
        st.caption("`in_estate` false = the act happened in the owner's lifetime and does not "
                   "enter the tarikah. Flip it only if you can show the act was void or a debt.")
        df = st.data_editor(pd.DataFrame(cfg["lifetime_acts"]), num_rows="dynamic",
                            width="stretch", key="ed_life",
                            column_config={"reason": st.column_config.TextColumn(width="large")})
        if st.button("Apply lifetime acts", key="ap_life"):
            cfg["lifetime_acts"] = df.where(pd.notna(df), None).to_dict("records")
            st.success("Applied.")

    with tabs[8]:
        st.subheader("Raw configuration")
        txt = st.text_area("config.json", json.dumps(cfg, indent=2, ensure_ascii=False),
                           height=420, key="raw_json")
        c1, c2, c3 = st.columns(3)
        if c1.button("Parse & apply", key="ap_raw"):
            try:
                st.session_state.cfg = json.loads(txt)
                st.success("Parsed. Press Save my settings to persist it to your account.")
                st.rerun()
            except json.JSONDecodeError as ex:
                st.error(f"Invalid JSON: {ex}")
        c2.download_button("Download config.json", txt, file_name="config.json",
                           mime="application/json")
        up = c3.file_uploader("Upload a config.json", type=["json"], key="up_raw")
        if up is not None:
            try:
                st.session_state.cfg = json.load(up)
                st.success("Loaded. Press Save my settings to persist it to your account.")
                st.rerun()
            except json.JSONDecodeError as ex:
                st.error(f"Invalid JSON: {ex}")

    st.divider()
    if st.button("💾 Save everything to my workspace", type="primary", key="save_all"):
        save_workspace(USER, cfg, note="saved from Settings")
        st.success("Saved to your workspace. Other heirs are unaffected.")
        st.rerun()
