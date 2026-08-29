"""
Hanafi (Sunni) fara'id share calculator.

Scope note
----------
This implements the branch of the Hanafi mirath rules needed for a
"parents + spouse + children" estate:

    husband / wife  ......... ashab al-furud (fixed sharers)
    father / mother ......... fixed sharers (father also 'asaba by residue)
    sons / daughters ........ 'asaba bi-nafsihi / bi-ghayrihi (2:1)

It handles:
  * blocking of the 1/3 -> 1/6 mother reduction when children exist
  * spouse quota halving when children exist
  * 'awl  (proportional abatement when fixed shares exceed unity)
  * radd  (return of surplus to non-spouse sharers when no residuary exists)

It deliberately does NOT model siblings, grandparents, grandchildren,
uncles, dhawu-l-arham, hajb by collaterals, mushtaraka/akdariyya, or
munasakha beyond the two-estate chain wired in engine.py.  Anything
outside the supported heir set raises, rather than silently guessing.
"""

from fractions import Fraction as F

SUPPORTED = {"husband", "wife", "father", "mother", "son", "daughter"}


def group_shares(heirs):
    """heirs: {group: count}. Returns (shares_by_group, notes)."""
    unknown = set(heirs) - SUPPORTED
    if unknown:
        raise ValueError(f"unsupported heir class(es) for this engine: {sorted(unknown)}")

    n = {g: int(heirs.get(g, 0)) for g in SUPPORTED}
    if n["husband"] and n["wife"]:
        raise ValueError("an estate cannot have both a husband and a wife heir")

    has_child = (n["son"] + n["daughter"]) > 0
    notes = []
    fixed = {}

    # --- spouse -----------------------------------------------------------
    if n["husband"]:
        fixed["husband"] = F(1, 4) if has_child else F(1, 2)
        notes.append("Husband: 1/4 (children present)" if has_child else "Husband: 1/2 (no child)")
    if n["wife"]:
        fixed["wife"] = F(1, 8) if has_child else F(1, 4)
        notes.append("Widow: 1/8 (children present) - Qur'an 4:12" if has_child
                     else "Widow: 1/4 (no child) - Qur'an 4:12")

    # --- mother -----------------------------------------------------------
    if n["mother"]:
        fixed["mother"] = F(1, 6) if has_child else F(1, 3)
        notes.append("Mother: 1/6 (child present)" if has_child else "Mother: 1/3 (no child)")

    # --- father -----------------------------------------------------------
    father_is_residuary = False
    if n["father"]:
        if n["son"]:
            fixed["father"] = F(1, 6)
            notes.append("Father: 1/6 fixed only (male descendant blocks his residue)")
        elif n["daughter"]:
            fixed["father"] = F(1, 6)
            father_is_residuary = True
            notes.append("Father: 1/6 fixed + residue (daughters only)")
        else:
            father_is_residuary = True
            notes.append("Father: pure residuary ('asaba) - no descendants")

    # --- daughters with no son are fixed sharers --------------------------
    if n["daughter"] and not n["son"]:
        fixed["daughter"] = F(1, 2) if n["daughter"] == 1 else F(2, 3)
        notes.append("Daughter(s): 1/2 (one)" if n["daughter"] == 1
                     else "Daughters: 2/3 shared (two or more), no son present")

    total_fixed = sum(fixed.values(), F(0))
    shares = dict(fixed)

    # --- 'awl -------------------------------------------------------------
    if total_fixed > 1:
        notes.append(f"'Awl applied: fixed shares summed to {total_fixed}; "
                     "all shares abated proportionally")
        shares = {g: v / total_fixed for g, v in fixed.items()}
        return _per_head(shares, n), notes

    residue = 1 - total_fixed

    # --- residuary ('asaba) -----------------------------------------------
    if residue > 0:
        if n["son"]:
            units = 2 * n["son"] + n["daughter"]
            shares["son"] = shares.get("son", F(0)) + residue * F(2 * n["son"], units)
            if n["daughter"]:
                shares["daughter"] = shares.get("daughter", F(0)) + residue * F(n["daughter"], units)
            notes.append("Residue to children as 'asaba bi-ghayrihi, male : female = 2 : 1 "
                         "- Qur'an 4:11")
        elif father_is_residuary:
            shares["father"] = shares.get("father", F(0)) + residue
            notes.append("Residue to father as nearest 'asaba")
        else:
            # --- radd -------------------------------------------------------
            eligible = {g: v for g, v in shares.items() if g not in ("husband", "wife")}
            base = sum(eligible.values(), F(0))
            if base > 0:
                for g, v in eligible.items():
                    shares[g] = v + residue * (v / base)
                notes.append("Radd: surplus returned pro-rata to blood sharers "
                             "(spouse excluded) - Hanafi position")
            else:
                notes.append("WARNING: surplus with no eligible heir; "
                             "escheat / bayt al-mal question - seek a mufti")

    return _per_head(shares, n), notes


def _per_head(group_shares_map, counts):
    """Return both the group total and the individual (per-head) share."""
    out = {}
    for g, total in group_shares_map.items():
        c = counts[g]
        if c == 0:
            continue
        out[g] = {"count": c, "group_share": total, "per_head": total / c}
    return out


def per_person(heirs_by_person, decedent_id=None):
    """
    heirs_by_person: [{'id':..,'name':..,'group':'son'|...}, ...]
    Returns ({person_id: Fraction}, notes)
    """
    counts = {}
    for h in heirs_by_person:
        counts[h["group"]] = counts.get(h["group"], 0) + 1
    gs, notes = group_shares(counts)
    out = {}
    for h in heirs_by_person:
        out[h["id"]] = gs[h["group"]]["per_head"]
    return out, notes
