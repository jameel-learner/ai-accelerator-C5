"""
Per-user workspace persistence.

Each signed-in user gets their own full snapshot of the estate configuration,
seeded from the shared baseline (`config.json`) on first sign-in.  From then on
their edits, policy switches and scenario settings are theirs alone - one heir
modelling "what if we charge notional rent" cannot disturb another heir's view.

Layout
------
    user_data/
        <slug>-<hash>.json              current workspace
        revisions/
            <slug>-<hash>/
                20260828T154233.json    capped rolling history

Files are written atomically (temp + os.replace) so an interrupted save cannot
truncate a workspace.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORE_DIR = os.path.join(BASE_DIR, "user_data")
REV_DIR = os.path.join(STORE_DIR, "revisions")

MAX_REVISIONS = 25
SCHEMA = 1


# --------------------------------------------------------------------------
# identity -> filename
# --------------------------------------------------------------------------
def user_key(email: str) -> str:
    """
    Stable, filesystem-safe key for an email address.

    The sha256 suffix is what actually guarantees uniqueness; the readable slug
    exists only so a human browsing user_data/ can tell the files apart.
    """
    e = (email or "").strip().lower()
    if not e:
        raise ValueError("cannot derive a workspace key from an empty email")
    digest = hashlib.sha256(e.encode("utf-8")).hexdigest()[:16]
    local = e.split("@")[0]
    slug = re.sub(r"[^a-z0-9]+", "-", local).strip("-")[:24] or "user"
    return f"{slug}-{digest}"


def state_path(email: str) -> str:
    return os.path.join(STORE_DIR, user_key(email) + ".json")


def _rev_dir(email: str) -> str:
    return os.path.join(REV_DIR, user_key(email))


def _ensure_dirs():
    os.makedirs(STORE_DIR, exist_ok=True)
    os.makedirs(REV_DIR, exist_ok=True)


def _atomic_write(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# read / write
# --------------------------------------------------------------------------
def load_state(email: str) -> dict | None:
    """Return the saved envelope {schema, email, name, saved_at, note, config} or None."""
    path = state_path(email)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict) or "config" not in payload:
        return None
    return payload


def save_state(email: str, config: dict, name: str | None = None,
               note: str = "", keep_revision: bool = True) -> dict:
    """Persist this user's workspace and snapshot the previous version."""
    _ensure_dirs()
    path = state_path(email)

    if keep_revision and os.path.exists(path):
        _snapshot(email, path)

    payload = {
        "schema": SCHEMA,
        "email": (email or "").strip().lower(),
        "name": name or "",
        "saved_at": dt.datetime.now().isoformat(timespec="seconds"),
        "note": note,
        "config": config,
    }
    _atomic_write(path, payload)
    return payload


def _snapshot(email: str, current_path: str):
    rd = _rev_dir(email)
    os.makedirs(rd, exist_ok=True)
    # millisecond precision: several saves inside one second must not collide,
    # and the name has to sort chronologically as plain text.
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S_%f")[:-3]
    dest = os.path.join(rd, f"{stamp}.json")
    n = 0
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(rd, f"{stamp}-{n}.json")
    try:
        shutil.copy2(current_path, dest)
    except OSError:
        return
    revs = sorted(f for f in os.listdir(rd) if f.endswith(".json"))
    for stale in revs[:-MAX_REVISIONS]:
        try:
            os.remove(os.path.join(rd, stale))
        except OSError:
            pass


def delete_state(email: str, drop_revisions: bool = False) -> bool:
    path = state_path(email)
    existed = os.path.exists(path)
    if existed:
        if not drop_revisions:
            _ensure_dirs()
            _snapshot(email, path)
        os.remove(path)
    if drop_revisions:
        shutil.rmtree(_rev_dir(email), ignore_errors=True)
    return existed


# --------------------------------------------------------------------------
# revisions
# --------------------------------------------------------------------------
def list_revisions(email: str) -> list[dict]:
    rd = _rev_dir(email)
    if not os.path.isdir(rd):
        return []
    out = []
    for f in sorted(os.listdir(rd), reverse=True):
        if not f.endswith(".json"):
            continue
        full = os.path.join(rd, f)
        meta = {"file": f, "path": full,
                "size": os.path.getsize(full),
                "saved_at": "", "note": ""}
        try:
            with open(full, "r", encoding="utf-8") as fh:
                p = json.load(fh)
            meta["saved_at"] = p.get("saved_at", "")
            meta["note"] = p.get("note", "")
        except (json.JSONDecodeError, OSError):
            pass
        out.append(meta)
    return out


def load_revision(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) and "config" in payload else None


# --------------------------------------------------------------------------
# admin view
# --------------------------------------------------------------------------
def list_states() -> list[dict]:
    """Every saved workspace - for the admin panel."""
    if not os.path.isdir(STORE_DIR):
        return []
    out = []
    for f in sorted(os.listdir(STORE_DIR)):
        if not f.endswith(".json"):
            continue
        full = os.path.join(STORE_DIR, f)
        try:
            with open(full, "r", encoding="utf-8") as fh:
                p = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        out.append({
            "email": p.get("email", ""),
            "name": p.get("name", ""),
            "saved_at": p.get("saved_at", ""),
            "note": p.get("note", ""),
            "revisions": len(list_revisions(p.get("email", ""))) if p.get("email") else 0,
            "file": f,
        })
    return out
