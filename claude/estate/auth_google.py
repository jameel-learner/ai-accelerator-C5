"""
GOOGLE SIGN-IN - CURRENTLY UNUSED.

Parked at the family's request; `auth.py` provides a simple hardcoded user
list instead.  To switch back, rename this file over auth.py, restore
`streamlit[auth]` in requirements.txt, and filling in
`.streamlit/secrets.toml` from the template in `.streamlit/secrets.toml.example`
(the app's own setup screen walks through the Google Cloud console steps).
It exposes the same login_gate()/render_user_card()/heir_for() API, so app.py
needs no changes.

Google sign-in gate, built on Streamlit's native OpenID Connect support
(`st.login` / `st.user` / `st.logout`, Streamlit >= 1.42).

Access control
--------------
This workbook holds a family's financial affairs, so sign-in alone is not
enough - anyone with a Google account can sign in.  A user reaches the app only
if their email appears in the allow-list, which is assembled from:

  1. `people[].email` in the SHARED baseline config.json  (the heirs), and
  2. `[access] allowed_emails` in .streamlit/secrets.toml  (advisors, admins).

The allow-list is deliberately read from the *baseline* config, never from the
signed-in user's own workspace - otherwise a user could edit their own copy and
grant themselves or others access.

If neither source lists anybody, the app refuses to grant access rather than
falling open, and tells you how to configure it.
"""

from __future__ import annotations

import os

import streamlit as st

import engine as E

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROVIDER = "google"


# --------------------------------------------------------------------------
# configuration probes
# --------------------------------------------------------------------------
def _secrets_section(name: str) -> dict:
    try:
        if name in st.secrets:
            return dict(st.secrets[name])
    except Exception:
        pass
    return {}


def auth_configured() -> bool:
    """True when secrets.toml carries a usable [auth] / [auth.google] block."""
    auth = _secrets_section("auth")
    if not auth:
        return False
    google = auth.get(PROVIDER)
    if not isinstance(google, dict):
        google = _secrets_section(f"auth.{PROVIDER}")
    return bool(auth.get("redirect_uri") and auth.get("cookie_secret")
                and google and google.get("client_id") and google.get("client_secret"))


def secrets_file_candidates() -> list[str]:
    """
    The paths Streamlit actually reads, asked of Streamlit itself rather than
    guessed - `.streamlit/secrets.toml` resolves against the *working directory*,
    not the script's directory, which is the usual reason a secrets file is
    written but never picked up.
    """
    try:
        from streamlit import config as _stconfig
        files = _stconfig.get_option("secrets.files")
        if files:
            return [os.path.abspath(f) for f in files]
    except Exception:
        pass
    return [
        os.path.expanduser("~/.streamlit/secrets.toml"),
        os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
    ]


def dev_mode_enabled() -> bool:
    """
    Unauthenticated local access, off unless explicitly switched on.

    Set FARAID_DEV_USER to an email address to work on the app without Google
    credentials. Never set it on a deployed instance.
    """
    return bool(os.environ.get("FARAID_DEV_USER"))


# --------------------------------------------------------------------------
# allow-list
# --------------------------------------------------------------------------
def _norm(e) -> str:
    return str(e or "").strip().lower()


def baseline_config() -> dict:
    """The shared config.json - the source of truth for who may sign in."""
    try:
        return E.load_config()
    except Exception:
        return {}


def allowed_emails() -> set[str]:
    cfg = baseline_config()
    emails = {_norm(p.get("email")) for p in cfg.get("people", []) if p.get("email")}
    access = _secrets_section("access")
    extra = access.get("allowed_emails") or []
    if isinstance(extra, str):
        extra = [extra]
    emails |= {_norm(e) for e in extra}
    return {e for e in emails if e}


def admin_emails() -> set[str]:
    access = _secrets_section("access")
    admins = access.get("admins") or []
    if isinstance(admins, str):
        admins = [admins]
    return {_norm(a) for a in admins if _norm(a)}


def is_admin(email: str) -> bool:
    return _norm(email) in admin_emails()


def heir_for(email: str, cfg: dict | None = None) -> str | None:
    """Map a signed-in address to the heir id it belongs to, if any."""
    cfg = cfg or baseline_config()
    target = _norm(email)
    for p in cfg.get("people", []):
        if _norm(p.get("email")) == target and target:
            return p["id"]
    return None


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------
def _user_record(email, name, picture, method) -> dict:
    return {
        "email": _norm(email),
        "name": name or _norm(email).split("@")[0],
        "picture": picture,
        "method": method,
        "is_admin": is_admin(email),
        "heir_id": heir_for(email),
    }


def login_gate() -> dict:
    """
    Return the signed-in user, or render the sign-in screen and stop the script.

    Never returns for an unauthenticated or unauthorised visitor.
    """
    if dev_mode_enabled():
        email = _norm(os.environ["FARAID_DEV_USER"])
        st.warning("**LOCAL DEV MODE — no authentication.** Running as "
                   f"`{email}` because `FARAID_DEV_USER` is set. "
                   "Unset it before deploying or sharing this instance.", icon="🔓")
        return _user_record(email, os.environ.get("FARAID_DEV_NAME", "Local developer"),
                            None, "dev")

    if not auth_configured():
        _render_setup_help()
        st.stop()

    if not getattr(st.user, "is_logged_in", False):
        _render_signin()
        st.stop()

    email = _norm(getattr(st.user, "email", ""))
    if not email:
        st.error("Google did not return an email address for this account. "
                 "The `email` scope is required.")
        if st.button("Sign out"):
            st.logout()
        st.stop()

    allow = allowed_emails()
    if not allow:
        _render_no_allowlist(email)
        st.stop()

    if email not in allow:
        _render_denied(email)
        st.stop()

    return _user_record(email, getattr(st.user, "name", None),
                        getattr(st.user, "picture", None), "google")


# --------------------------------------------------------------------------
# screens
# --------------------------------------------------------------------------
def _shell(title: str, icon: str = "⚖️"):
    st.markdown(f"<h1 style='margin-bottom:0'>{icon} {title}</h1>", unsafe_allow_html=True)


def _render_signin():
    _shell("Fara'id Estate Workbook")
    st.caption("Hanafi inheritance computation for the estate of Hanif & Khudsia")
    st.write("")
    c = st.columns([1, 1.4, 1])
    with c[1]:
        st.info("This workbook contains the family's financial affairs. "
                "Sign in with the Google account registered against your name.")
        if st.button("Sign in with Google", type="primary", width="stretch"):
            st.login(PROVIDER)
        st.caption("Your scenario settings are saved privately to your own account. "
                   "Other heirs cannot see or change them.")


def _render_denied(email: str):
    _shell("Access not granted", "🔒")
    st.error(f"**{email}** is not on the access list for this workbook.")
    st.write("Ask whoever maintains the workbook to add your address — either as "
             "`email` against your name in the shared `config.json`, or under "
             "`[access] allowed_emails` in `.streamlit/secrets.toml`.")
    if st.button("Sign out and try another account"):
        st.logout()


def _render_no_allowlist(email: str):
    _shell("No access list configured", "⚠️")
    st.error("Sign-in succeeded, but **nobody is on the access list**, so access is refused "
             "rather than left open to any Google account.")
    st.write(f"You signed in as **{email}**. To let people in, do either of these:")
    st.markdown(
        "1. Add an `email` field to each person in the shared `config.json` "
        "(the Settings → People editor writes this), **or**\n"
        "2. Add addresses to `.streamlit/secrets.toml`:"
    )
    st.code('[access]\nallowed_emails = ["you@gmail.com", "sibling@gmail.com"]\n'
            'admins = ["you@gmail.com"]', language="toml")
    if st.button("Sign out"):
        st.logout()


def _render_setup_help():
    _shell("Google sign-in is not configured", "🔧")
    st.write("Streamlit needs an `[auth]` block in `secrets.toml` before `st.login()` will work. "
             "This instance reads exactly these files:")
    for p in secrets_file_candidates():
        st.markdown(f"- `{p}` {'✅ found' if os.path.exists(p) else '— not present'}")
    st.caption(f"`.streamlit/secrets.toml` is resolved against the working directory, which is "
               f"currently `{os.getcwd()}`. The app lives in `{APP_DIR}` — if those differ, "
               "start the app with `cd estate` first so the paths line up.")

    st.subheader("1. Create the Google OAuth client")
    st.markdown("""
In the [Google Cloud console](https://console.cloud.google.com/apis/credentials):

1. **APIs & Services → OAuth consent screen** — choose *External*, fill in the app name and
   your support email. While the app is in *Testing*, add each family member as a **Test user**.
2. **Credentials → Create credentials → OAuth client ID → Web application**.
3. Under **Authorised redirect URIs** add exactly the `redirect_uri` you configure below —
   for local use that is `http://localhost:8512/oauth2callback`.
4. Copy the **Client ID** and **Client secret**.
""")

    st.subheader("2. Write the secrets file")
    st.code('''[auth]
redirect_uri = "http://localhost:8512/oauth2callback"
cookie_secret = "PASTE-A-LONG-RANDOM-STRING-HERE"

[auth.google]
client_id = "xxxxx.apps.googleusercontent.com"
client_secret = "GOCSPX-xxxxxxxx"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[access]
allowed_emails = ["heir1@gmail.com", "heir2@gmail.com"]
admins = ["heir1@gmail.com"]
''', language="toml")
    st.caption("Generate a cookie_secret with:  python -c \"import secrets;print(secrets.token_urlsafe(48))\"")

    st.subheader("3. Install the auth extra and restart")
    st.code('pip install "streamlit[auth]"', language="bash")

    st.divider()
    st.info("**Just want to keep working locally without Google?** Set `FARAID_DEV_USER` "
            "to any email address and restart — the app will run unauthenticated under that "
            "identity, with its own workspace. Do not do this on a shared or deployed instance.",
            icon="🔓")
    st.code('$env:FARAID_DEV_USER="you@example.com"; streamlit run app.py', language="powershell")


def render_user_card(user: dict, source_label: str = ""):
    """Sidebar identity block."""
    cols = st.columns([1, 3]) if user.get("picture") else [None, st.container()]
    if user.get("picture"):
        cols[0].image(user["picture"], width=44)
        target = cols[1]
    else:
        target = cols[1]
    with target:
        st.markdown(f"**{user['name']}**")
        badges = []
        if user.get("heir_id"):
            badges.append(user["heir_id"])
        if user.get("is_admin"):
            badges.append("admin")
        if user.get("method") == "dev":
            badges.append("dev mode")
        st.caption(user["email"] + (f"  ·  {' · '.join(badges)}" if badges else ""))
    if source_label:
        st.caption(source_label)
