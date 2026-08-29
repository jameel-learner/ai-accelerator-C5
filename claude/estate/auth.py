"""
Simple hardcoded user list - no authentication.

Five fixed users, one per heir.  Picking a name loads that user's saved
workspace; everything they change and save is stored against their address
alone (see store.py).

THIS IS IDENTIFICATION, NOT AUTHENTICATION.  There are no passwords: anyone
who can reach the app can select any of the five names and read or overwrite
that person's workspace.  That is fine for a laptop or a machine the family
controls, and not fine for anything reachable from the internet.  The Google
OAuth version is parked in `auth_google.py` and exposes the same API - rename
it over this file to switch back.

The public API is deliberately identical to the OAuth module:
    login_gate()            -> user dict, or renders the picker and stops
    render_user_card(user)  -> sidebar identity block
    heir_for(email, cfg)    -> heir id for an address
"""

from __future__ import annotations

import streamlit as st

import engine as E
import store

# --------------------------------------------------------------------------
# the five users
# --------------------------------------------------------------------------
USERS = [
    {"email": "suhail@gmail.com",   "name": "Suhail",   "heir_id": "B1"},
    {"email": "fouzia@gmail.com",   "name": "Fouzia",   "heir_id": "S1"},
    {"email": "jameel@gmail.com",   "name": "Jameel",   "heir_id": "B2"},
    {"email": "shabanaz@gmail.com", "name": "Shabanaz", "heir_id": "S2"},
    {"email": "shahnaz@gmail.com",  "name": "Shahnaz",  "heir_id": "S3"},
]

# Who may publish their configuration as the shared baseline and see the list
# of saved workspaces.  With no authentication this is a convenience, not a
# security boundary - anyone can select any name.
ADMINS = {u["email"] for u in USERS}

BY_EMAIL = {u["email"]: u for u in USERS}

# Which query parameter remembers the selection across a page reload.
QP_USER = "user"


def _norm(e) -> str:
    return str(e or "").strip().lower()


# --------------------------------------------------------------------------
# lookups
# --------------------------------------------------------------------------
def known_emails() -> list[str]:
    return [u["email"] for u in USERS]


def is_admin(email: str) -> bool:
    return _norm(email) in ADMINS


def heir_for(email: str, cfg: dict | None = None) -> str | None:
    """
    Heir id for an address.

    The hardcoded table is authoritative.  A `people[].email` in the config is
    honoured as a fallback so the mapping survives someone renaming the users.
    """
    target = _norm(email)
    if target in BY_EMAIL:
        return BY_EMAIL[target]["heir_id"]
    for p in (cfg or {}).get("people", []):
        if _norm(p.get("email")) == target and target:
            return p["id"]
    return None


def _user_record(email: str) -> dict:
    u = BY_EMAIL[_norm(email)]
    return {
        "email": u["email"],
        "name": u["name"],
        "picture": None,
        "method": "local",
        "is_admin": is_admin(u["email"]),
        "heir_id": u["heir_id"],
    }


# --------------------------------------------------------------------------
# session handling
# --------------------------------------------------------------------------
def _clear_user_session():
    """
    Drop every piece of per-user session state.

    Widget values (the data editors especially) are keyed and would otherwise
    survive a user switch and be written into the next user's workspace, so the
    whole session is wiped rather than just the config.
    """
    for k in list(st.session_state.keys()):
        if k != QP_USER:
            del st.session_state[k]


def set_user(email: str):
    _clear_user_session()
    st.session_state["user_email"] = _norm(email)
    st.query_params[QP_USER] = _norm(email)


def switch_user():
    _clear_user_session()
    st.session_state.pop("user_email", None)
    try:
        del st.query_params[QP_USER]
    except (KeyError, AttributeError):
        pass


def login_gate() -> dict:
    """Return the selected user, or render the picker and stop the script."""
    email = _norm(st.session_state.get("user_email"))

    # a reload loses session state, so fall back to the query parameter
    if email not in BY_EMAIL:
        qp = _norm(st.query_params.get(QP_USER))
        if qp in BY_EMAIL:
            st.session_state["user_email"] = qp
            email = qp

    if email not in BY_EMAIL:
        _render_picker()
        st.stop()

    return _user_record(email)


# --------------------------------------------------------------------------
# screens
# --------------------------------------------------------------------------
def _render_picker():
    st.markdown("<h1 style='margin-bottom:0'>⚖️ Fara'id Estate Workbook</h1>",
                unsafe_allow_html=True)
    st.caption("Hanafi inheritance computation for the estate of Hanif & Khudsia")
    st.write("")
    st.subheader("Who are you?")
    st.caption("Your settings, scenarios and edits are saved separately for each name "
               "and reloaded the next time you pick it.")

    try:
        cfg = E.load_config()
        people = E.people_index(cfg)
    except Exception:
        people = {}

    cols = st.columns(len(USERS))
    for col, u in zip(cols, USERS):
        with col:
            person = people.get(u["heir_id"], {})
            relation = person.get("relation", "")
            saved = store.load_state(u["email"])

            st.markdown(f"### {u['name']}")
            st.caption(f'{u["heir_id"]} · {relation}' if relation else u["heir_id"])
            if saved:
                st.success(f'Saved {saved.get("saved_at", "")[:16].replace("T", " ")}',
                           icon="💾")
            else:
                st.info("No saved settings yet", icon="🆕")
            if st.button("Open", key=f'pick_{u["email"]}', width="stretch",
                         type="primary"):
                set_user(u["email"])
                st.rerun()
            st.caption(u["email"])

    st.divider()
    st.warning("**No password is required.** Anyone who can reach this app can open any of "
               "the five workspaces. Run it only on a machine the family controls.", icon="🔓")


def render_user_card(user: dict, source_label: str = ""):
    """Sidebar identity block."""
    st.markdown(f"**{user['name']}**")
    badges = [b for b in (user.get("heir_id"), "admin" if user.get("is_admin") else None) if b]
    st.caption(user["email"] + (f"  ·  {' · '.join(badges)}" if badges else ""))
    if source_label:
        st.caption(source_label)
