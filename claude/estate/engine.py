"""
Estate engine: valuation, ownership windows, and the income/expense ledger.

Design rule that drives everything here
---------------------------------------
Nothing that happened while an owner was alive belongs in his tarikah.
So every money flow is cut at each death date and each resulting segment is
allocated with the ownership map that was actually in force during it:

    W0  ..............  < 2022-07-20  -> the father owned 100%. OUT OF SCOPE.
    W1  2022-07-20 .. 2025-10-28      -> widow 1/8, each son 1/4, each dau 1/8
    W2  >= 2025-10-28                 -> each son 2/7, each daughter 1/7

The widow's W1 entitlement is not hers to keep - she died undistributed, so it
rolls into her own tarikah (munasakha) and is re-split 2:1 among the five.
That re-split happens to restore the same 2:1 ratio, which is why the
consolidated post-2022 map equals the W2 map.  The two-stage view is still
kept separately because it is the legally correct chain and because it matters
if any heir dies, disclaims, or settles before the partition.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
from fractions import Fraction as F

import pandas as pd

from faraid import per_person

DAYS_PER_MONTH = 30.436875
DAYS_PER_YEAR = 365.2425

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

W_LIFETIME = "W0 lifetime (father alive)"
W_POST_F = "W1 after father's death"
W_POST_M = "W2 after mother's death"


# --------------------------------------------------------------------------
# config io
# --------------------------------------------------------------------------
def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_config(cfg: dict, path: str = CONFIG_PATH) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def d(s):
    if s is None:
        return None
    if isinstance(s, dt.date):
        return s
    return dt.date.fromisoformat(str(s)[:10])


def people_index(cfg):
    return {p["id"]: p for p in cfg["people"]}


def name_of(cfg, pid):
    p = people_index(cfg).get(pid)
    return f'{p["name"]} ({pid})' if p else str(pid)


def heir_ids(cfg):
    """The five living children, in config order."""
    return [h["id"] for h in _estate(cfg, "EM")["heirs"]]


def _estate(cfg, eid):
    for e in cfg["estates"]:
        if e["id"] == eid:
            return e
    raise KeyError(eid)


# --------------------------------------------------------------------------
# fara'id
# --------------------------------------------------------------------------
def shares(cfg):
    """
    Returns a dict with:
      ef      : {person: Fraction}  father's tarikah
      em      : {person: Fraction}  mother's tarikah
      final   : {person: Fraction}  combined entitlement in the father's corpus
      notes   : list[str]
    """
    ef_def = _estate(cfg, "EF")
    em_def = _estate(cfg, "EM")

    ef, notes_f = per_person(ef_def["heirs"])
    em, notes_m = per_person(em_def["heirs"])

    widow = ef.get(em_def["inherits_from"]["as_person"], F(0))
    final = {}
    for pid, frac in ef.items():
        if pid == em_def["inherits_from"]["as_person"]:
            continue
        final[pid] = frac + widow * em.get(pid, F(0))
    for pid, frac in em.items():
        final.setdefault(pid, widow * frac)

    return {
        "ef": ef,
        "em": em,
        "final": final,
        "widow_share": widow,
        "notes_father": notes_f,
        "notes_mother": notes_m,
    }


def ownership_maps(cfg):
    """Ownership map per window, plus the consolidated post-death map."""
    s = shares(cfg)
    return {
        W_LIFETIME: {cfg["estates"][0]["decedent"]: F(1)},
        W_POST_F: dict(s["ef"]),
        W_POST_M: dict(s["em"]),
        "consolidated": dict(s["final"]),
    }


# --------------------------------------------------------------------------
# valuation
# --------------------------------------------------------------------------
def property_value(p, policy):
    if p.get("disputed") and not policy.get("include_disputed_p6", False):
        return 0.0
    if p.get("rate_per_sqft"):
        gross = float(p["area_sqft"]) * float(p["rate_per_sqft"])
    else:
        gross = float(p.get("lump_value") or 0.0)
    return gross * float(p.get("ownership_share", 1.0))


def valuation(cfg):
    policy = cfg["policy"]
    rows = []
    for p in cfg["properties"]:
        gross = (float(p["area_sqft"]) * float(p["rate_per_sqft"])
                 if p.get("rate_per_sqft") else float(p.get("lump_value") or 0.0))
        net = property_value(p, policy)
        rows.append({
            "id": p["id"], "name": p["name"], "kind": p["kind"],
            "area_sqft": p["area_sqft"],
            "gross_value": gross,
            "ownership_share": p.get("ownership_share", 1.0),
            "estate_value": net,
            "disputed": bool(p.get("disputed")),
            "excluded": bool(p.get("disputed")) and not policy.get("include_disputed_p6"),
            "note": p.get("note", ""),
        })
    df = pd.DataFrame(rows)

    advances = sum(float(u.get("advance") or 0)
                   for u in cfg["rent_units"] if u.get("estate_owned"))

    liabs = []
    for l in cfg["estate_liabilities"]:
        amt = l["amount"]
        if amt == "AUTO_ADVANCES":
            amt = advances if policy.get("deduct_tenant_advances", True) else 0.0
        liabs.append({"id": l["id"], "label": l["label"],
                      "amount": float(amt), "note": l.get("note", "")})
    ldf = pd.DataFrame(liabs)

    gross_corpus = float(df["estate_value"].sum())
    total_liab = float(ldf["amount"].sum())
    return {
        "properties": df,
        "liabilities": ldf,
        "tenant_advances": advances,
        "gross_corpus": gross_corpus,
        "total_liabilities": total_liab,
        "net_corpus": gross_corpus - total_liab,
    }


# --------------------------------------------------------------------------
# time helpers
# --------------------------------------------------------------------------
def _overlap(a0, a1, b0, b1):
    lo = max(a0, b0)
    hi = min(a1, b1)
    return (lo, hi) if hi > lo else None


def _amount(stream, seg_start, seg_end):
    days = (seg_end - seg_start).days
    if days <= 0:
        return 0.0
    amt = float(stream["amount"])
    per = stream.get("period", "monthly")
    if per == "monthly":
        return amt * days / DAYS_PER_MONTH
    if per == "annual":
        return amt * days / DAYS_PER_YEAR
    if per == "oneoff":
        return amt
    raise ValueError(f"unknown period {per!r} on stream {stream.get('id')}")


def windows(cfg, as_of):
    fd = d(_estate(cfg, "EF")["death_date"])
    md = d(_estate(cfg, "EM")["death_date"])
    far = dt.date(1900, 1, 1)
    return [
        (W_LIFETIME, far, fd),
        (W_POST_F, fd, md),
        (W_POST_M, md, as_of),
    ]


# --------------------------------------------------------------------------
# ledger
# --------------------------------------------------------------------------
def ledger(cfg, as_of=None):
    """
    Explode every stream into (stream x window) segments with the amount that
    accrued in that window.  No allocation yet - that is `allocate`.
    """
    policy = cfg["policy"]
    as_of = d(as_of or policy.get("as_of") or cfg["meta"]["as_of"])
    wins = windows(cfg, as_of)

    rows = []
    for st in cfg["streams"]:
        if st.get("assumed") and not policy.get("allow_assumed_streams", True):
            continue
        s0 = d(st["start"])
        s1 = d(st["end"]) if st.get("end") else as_of
        if s1 > as_of:
            s1 = as_of
        for wname, w0, w1 in wins:
            ov = _overlap(s0, s1, w0, w1)
            if not ov:
                continue
            seg0, seg1 = ov
            rows.append({
                "stream_id": st["id"],
                "kind": st["kind"],
                "property": st.get("property"),
                "unit": st.get("unit"),
                "actor": st["actor"],
                "category": st.get("category", st["kind"]),
                "window": wname,
                "seg_start": seg0,
                "seg_end": seg1,
                "months": (seg1 - seg0).days / DAYS_PER_MONTH,
                "rate": float(st["amount"]),
                "period": st.get("period"),
                "amount": _amount(st, seg0, seg1),
                "assumed": bool(st.get("assumed")),
                "note": st.get("note", ""),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["stream_id", "kind", "property", "unit", "actor",
                                   "category", "window", "seg_start", "seg_end",
                                   "months", "rate", "period", "amount", "assumed", "note"])
    return df, as_of


def _active_map(cfg, basis):
    """Which ownership map to use for each window, given the selected basis."""
    om = ownership_maps(cfg)
    if basis == "father_death":
        # one reckoning date: everything post-death allocated on the father's map
        return {W_POST_F: om[W_POST_F], W_POST_M: om[W_POST_F]}
    if basis == "mother_death":
        return {W_POST_F: om[W_POST_M], W_POST_M: om[W_POST_M]}
    # timeline (default): each window on its own map
    return {W_POST_F: om[W_POST_F], W_POST_M: om[W_POST_M]}


def allocate(cfg, as_of=None, basis=None):
    """
    Allocate each ledger segment to the heirs entitled during that segment,
    and net it off against who actually collected/paid.

    Returns dict:
      ledger      : segment dataframe (with in_scope flag)
      alloc       : long dataframe [person, stream_id, window, kind, entitled, received, paid, liable, net]
      positions   : per-person summary
      totals      : dict of headline numbers
    """
    policy = cfg["policy"]
    basis = basis or policy.get("basis", "timeline")
    led, as_of = ledger(cfg, as_of)
    maps = _active_map(cfg, basis)

    charge_occ = policy.get("charge_occupation_rent", False)
    include_pre = policy.get("include_pre_death_flows", False)
    reimburse = policy.get("expenses_are_reimbursable", True)

    def in_scope(r):
        if r["kind"] == "notional_rent" and not charge_occ:
            return False
        if r["window"] == W_LIFETIME:
            return bool(include_pre)
        if basis == "mother_death" and r["window"] == W_POST_F:
            return False
        return True

    led = led.copy()
    led["in_scope"] = led.apply(in_scope, axis=1) if len(led) else []
    if len(led):
        led["excl_reason"] = led.apply(_excl_reason(charge_occ, include_pre, basis), axis=1)
    else:
        led["excl_reason"] = []

    recs = []
    for _, r in led[led["in_scope"]].iterrows() if len(led) else []:
        if r["window"] == W_LIFETIME:
            # pre-death flows, if included, are a debt to / credit from the
            # father's tarikah: allocate on the father-estate map.
            omap = maps[W_POST_F]
        else:
            omap = maps[r["window"]]
        amt = float(r["amount"])
        income = r["kind"] in ("rent", "notional_rent")
        for pid, frac in omap.items():
            fr = float(frac)
            rec = {
                "person": pid, "stream_id": r["stream_id"], "kind": r["kind"],
                "category": r["category"], "property": r["property"],
                "unit": r["unit"], "window": r["window"], "actor": r["actor"],
                "share": fr,
                "entitled": amt * fr if income else 0.0,
                "received": amt if (income and pid == r["actor"]) else 0.0,
                "liable": amt * fr if (not income and reimburse) else 0.0,
                "paid": amt if (not income and pid == r["actor"] and reimburse) else 0.0,
            }
            rec["net"] = (rec["entitled"] - rec["received"]) + (rec["paid"] - rec["liable"])
            recs.append(rec)

    alloc = pd.DataFrame(recs)
    if alloc.empty:
        alloc = pd.DataFrame(columns=["person", "stream_id", "kind", "category", "property",
                                      "unit", "window", "actor", "share", "entitled",
                                      "received", "liable", "paid", "net"])

    everyone = list(dict.fromkeys(
        [h["id"] for h in _estate(cfg, "EF")["heirs"]] + heir_ids(cfg)))
    pos = (alloc.groupby("person")[["entitled", "received", "liable", "paid", "net"]]
           .sum().reindex(everyone).fillna(0.0).reset_index())
    pos["name"] = pos["person"].map(lambda p: people_index(cfg)[p]["name"])
    pos["relation"] = pos["person"].map(lambda p: people_index(cfg)[p]["relation"])
    pos = pos[["person", "name", "relation", "entitled", "received", "liable", "paid", "net"]]

    inscope = led[led["in_scope"]] if len(led) else led
    totals = {
        "as_of": as_of,
        "basis": basis,
        "income_in_scope": float(inscope.loc[inscope["kind"].isin(["rent", "notional_rent"]), "amount"].sum()) if len(inscope) else 0.0,
        "expense_in_scope": float(inscope.loc[inscope["kind"] == "expense", "amount"].sum()) if len(inscope) else 0.0,
        "out_of_scope": float(led.loc[~led["in_scope"], "amount"].sum()) if len(led) else 0.0,
    }
    totals["net_estate_income"] = totals["income_in_scope"] - (
        totals["expense_in_scope"] if reimburse else 0.0)

    return {"ledger": led, "alloc": alloc, "positions": pos, "totals": totals,
            "as_of": as_of, "basis": basis}


def _excl_reason(charge_occ, include_pre, basis):
    def f(r):
        if r["kind"] == "notional_rent" and not charge_occ:
            return "Notional rent switched OFF (Hanafi: a co-owner in occupation of musha' owes no ujrat al-mithl)"
        if r["window"] == W_LIFETIME and not include_pre:
            return "Pre-death flow - the father was alive and owned 100%; outside the fara'id"
        if basis == "mother_death" and r["window"] == W_POST_F:
            return "Excluded by the 'mother's death' reckoning basis"
        return ""
    return f


# --------------------------------------------------------------------------
# gold
# --------------------------------------------------------------------------
def gold_analysis(cfg):
    g = cfg["gold"]
    policy = cfg["policy"]
    s = shares(cfg)
    rate = float(g.get("rate_per_gram") or 0)

    total = float(g["total_grams"])
    claim = float(g.get("s1_claim_grams") or 0)
    claimant = g.get("claimant", "S1")
    gift_valid = bool(policy.get("s1_gold_gift_valid"))
    gifted = claim if gift_valid else 0.0
    pool = total - gifted

    ids = heir_ids(cfg)
    # What the family actually did: the balance after the claimed bangles was split
    # five ways, and the claimant kept the bangles on top.  Measure every heir
    # against the SAME pool - so the claimed grams count as "taken from the pool"
    # only when the gift is held invalid and the bangles fall back into it.
    split_each = (total - claim) / len(ids)

    rows = []
    for pid in ids:
        if policy.get("gold_split_rule", "shariah") == "equal_5":
            entitled_g = pool / len(ids)
            rule = "equal 5-way (sulh)"
        else:
            entitled_g = pool * float(s["em"][pid])
            rule = "2:1 shariah"
        actual_g = split_each + (claim if (pid == claimant and not gift_valid) else 0.0)
        rows.append({
            "person": pid,
            "name": people_index(cfg)[pid]["name"],
            "relation": people_index(cfg)[pid]["relation"],
            "rule": rule,
            "entitled_g": entitled_g,
            "actually_taken_g": actual_g,
            "delta_g": actual_g - entitled_g,
            "delta_value": (actual_g - entitled_g) * rate,
        })
    df = pd.DataFrame(rows)
    return {
        "table": df,
        "pool_grams": pool,
        "gifted_grams": gifted,
        "rate": rate,
        "pool_value": pool * rate,
        "note": g.get("s1_claim_note", ""),
        "split_note": g.get("actual_split_note", ""),
    }


# --------------------------------------------------------------------------
# final settlement
# --------------------------------------------------------------------------
def settlement(cfg, as_of=None, basis=None):
    """
    Bring the corpus entitlement, the income/expense net position, the gold and
    the optional gift set-off together into one payable/receivable per heir.
    """
    policy = cfg["policy"]
    val = valuation(cfg)
    res = allocate(cfg, as_of=as_of, basis=basis)
    s = shares(cfg)
    gold = gold_analysis(cfg)

    basis_used = res["basis"]
    corpus_map = {"father_death": s["ef"], "mother_death": s["em"]}.get(basis_used, s["final"])

    people = list(corpus_map.keys())

    # Munasakha of the mother's OWN flow position.  Under the timeline basis she
    # was a 1/8 stakeholder in all income between the two deaths; whatever she
    # over- or under-drew died with her and re-splits among the five per EM.
    mother_id = _estate(cfg, "EM").get("inherits_from", {}).get("as_person")
    pos = res["positions"]
    mother_net = 0.0
    if mother_id and mother_id not in corpus_map:
        mother_net = float(pos.loc[pos["person"] == mother_id, "net"].sum())

    rows = []
    for pid in people:
        frac = corpus_map[pid]
        corpus = val["net_corpus"] * float(frac)
        net_flow = float(pos.loc[pos["person"] == pid, "net"].sum())
        net_flow += mother_net * float(s["em"].get(pid, 0))
        gld = gold["table"].loc[gold["table"]["person"] == pid, "delta_value"]
        gold_adj = -float(gld.iloc[0]) if len(gld) else 0.0
        rows.append({
            "person": pid,
            "name": people_index(cfg)[pid]["name"],
            "relation": people_index(cfg)[pid]["relation"],
            "share_fraction": str(frac),
            "share_pct": float(frac) * 100,
            "corpus_entitlement": corpus,
            "income_expense_net": net_flow,
            "gold_adjustment": gold_adj,
            "gift_setoff": 0.0,
            "total_entitlement": corpus + net_flow + gold_adj,
        })
    df = pd.DataFrame(rows)

    if policy.get("treat_2015_gift_as_advance"):
        gifts = [a for a in cfg["lifetime_acts"]
                 if a["kind"] == "hiba" and a.get("beneficiary")]
        for a in gifts:
            b = a["beneficiary"]
            amt = float(a["amount"])
            if b not in set(df["person"]):
                continue
            df.loc[df["person"] == b, "gift_setoff"] -= amt
            others = df["person"] != b
            n_units = df.loc[others, "share_pct"].sum()
            if n_units > 0:
                df.loc[others, "gift_setoff"] += amt * df.loc[others, "share_pct"] / n_units
        df["total_entitlement"] = (df["corpus_entitlement"] + df["income_expense_net"]
                                   + df["gold_adjustment"] + df["gift_setoff"])

    return {"table": df, "valuation": val, "flows": res, "shares": s, "gold": gold,
            "mother_net_rolled": mother_net,
            "as_of": res["as_of"], "basis": basis_used}


# --------------------------------------------------------------------------
# scope register (the in / out segregation, as data)
# --------------------------------------------------------------------------
def scope_register(cfg, as_of=None, basis=None):
    """One row per fact pattern, labelled IN or OUT of the fara'id, with reason."""
    res = allocate(cfg, as_of=as_of, basis=basis)
    led = res["ledger"]
    rows = []

    for a in cfg["lifetime_acts"]:
        rows.append({
            "ref": a["id"], "when": a["date"], "what": a["label"],
            "actor": a.get("actor"), "amount": float(a.get("amount") or 0),
            "scope": "IN" if a.get("in_estate") else "OUT",
            "bucket": "Lifetime act (tasarruf of a living owner)",
            "reason": a["reason"],
        })

    if len(led):
        g = (led.groupby(["stream_id", "kind", "window", "actor", "in_scope", "excl_reason"],
                         dropna=False)["amount"].sum().reset_index())
        for _, r in g.iterrows():
            rows.append({
                "ref": r["stream_id"], "when": r["window"],
                "what": f'{r["kind"]} by {r["actor"]}',
                "actor": r["actor"], "amount": float(r["amount"]),
                "scope": "IN" if r["in_scope"] else "OUT",
                "bucket": "Estate income" if r["kind"] in ("rent", "notional_rent") else "Estate expense",
                "reason": r["excl_reason"] or "Accrued on jointly-owned tarikah property after death; shared pro rata",
            })

    g = cfg["gold"]
    rows.append({
        "ref": "G1", "when": _estate(cfg, "EM")["death_date"],
        "what": f'Gold {g["total_grams"]}g left by the mother',
        "actor": "M", "amount": float(g["total_grams"]) * float(g["rate_per_gram"]),
        "scope": "IN", "bucket": "Mother's tarikah (movables)",
        "reason": "Her own mulk (mahr / personal jewellery) - divides 2:1 among the five children.",
    })
    rows.append({
        "ref": "G2", "when": _estate(cfg, "EM")["death_date"],
        "what": f'S1 claim to {g["s1_claim_grams"]}g bangles as a gift',
        "actor": "S1", "amount": float(g["s1_claim_grams"]) * float(g["rate_per_gram"]),
        "scope": "OUT" if cfg["policy"].get("s1_gold_gift_valid") else "IN",
        "bucket": "Contested - hiba vs wasiyya",
        "reason": g["s1_claim_note"],
    })
    rows.append({
        "ref": "G3", "when": "post-death", "what": "Equal 5-way split of the gold actually carried out",
        "actor": "all", "amount": 0.0, "scope": "IN",
        "bucket": "Deviation from fara'id - needs sulh",
        "reason": g["actual_split_note"],
    })

    for p in cfg["properties"]:
        if p.get("disputed"):
            rows.append({
                "ref": p["id"], "when": "pending", "what": f'{p["name"]} - title under litigation',
                "actor": "-", "amount": property_value(p, cfg["policy"]),
                "scope": "IN" if cfg["policy"].get("include_disputed_p6") else "SUSPENDED",
                "bucket": "Mawquf asset",
                "reason": "Ownership is sub judice. Shares vest in principle but cannot be quantified or partitioned until the decree; distribute the rest and keep this asset in a separate schedule.",
            })
        if float(p.get("ownership_share", 1.0)) < 1.0:
            rows.append({
                "ref": p["id"], "when": "-",
                "what": f'{p["name"]} - only {float(p["ownership_share"])*100:.0f}% is estate property',
                "actor": "-", "amount": property_value(p, cfg["policy"]),
                "scope": "PARTIAL", "bucket": "Third-party co-ownership",
                "reason": "The partner's share was never the deceased's mulk and never entered the tarikah.",
            })

    sold = [u for u in cfg["rent_units"] if not u.get("estate_owned")]
    if sold:
        rows.append({
            "ref": "P2-sold", "when": "-",
            "what": f'{len(sold)} flats in P2 sold to outside owners ({", ".join(u["unit"] for u in sold)})',
            "actor": "-", "amount": 0.0, "scope": "OUT", "bucket": "Third-party property",
            "reason": "Conveyed before death; neither the flats nor their rents are estate property.",
        })

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# formatting helpers
# --------------------------------------------------------------------------
def inr(x, decimals=0):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e7:
        return f"{sign}Rs {x/1e7:,.2f} cr"
    if x >= 1e5:
        return f"{sign}Rs {x/1e5:,.2f} L"
    return f"{sign}Rs {x:,.{decimals}f}"


def inr_full(x):
    try:
        return f"Rs {float(x):,.0f}"
    except (TypeError, ValueError):
        return str(x)


def clone(cfg):
    return copy.deepcopy(cfg)
