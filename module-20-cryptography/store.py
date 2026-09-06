"""
Storage backend for the lab portal.

Two interchangeable backends, selected automatically:
  * Supabase (Postgres via the PostgREST API)  -> used when SUPABASE_URL and
    SUPABASE_SERVICE_KEY are set (i.e. on Vercel / any hosted deploy).
  * Local JSON files under .lab/ (or $SIS_DATA_DIR) -> used for local dev.

Only standard-library HTTP is used (urllib), so there are no extra dependencies
to install on Vercel.

Tables (see supabase/schema.sql):
  users(username text primary key, salt text, pw_hash text, created_at timestamptz)
  progress(username text primary key, solved jsonb, attempts jsonb, updated_at timestamptz)
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# local-file fallback locations (used only when Supabase is not configured)
_LAB = Path(__file__).resolve().parent / ".lab"
_DATA = Path(os.environ.get("SIS_DATA_DIR") or str(_LAB))
_USERS = _DATA / "users.json"
_PROGRESS = _DATA / "progress"


def backend():
    return "supabase" if USE_SUPABASE else "files"


# --------------------------------------------------------------------------
# Supabase (PostgREST) helpers
# --------------------------------------------------------------------------
def _sb(method, path, params=None, body=None, prefer=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Supabase {method} {path} -> {e.code}: {detail}")


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------
def get_user(username):
    """Return {'username','salt','pw_hash'} for a case-insensitive match, or None."""
    if USE_SUPABASE:
        rows = _sb("GET", "users",
                   params={"username_lower": f"eq.{(username or '').lower()}",
                           "select": "username,salt,pw_hash", "limit": 1})
        return rows[0] if rows else None
    users = _read_json(_USERS, {})
    key = next((u for u in users if u.lower() == (username or "").lower()), None)
    if not key:
        return None
    r = users[key]
    return {"username": key, "salt": r["salt"], "pw_hash": r.get("pw_hash") or r.get("hash")}


def create_user(username, salt, pw_hash):
    """Insert a new user. Returns (ok, message)."""
    if get_user(username) is not None:
        return False, "That username is already taken."
    if USE_SUPABASE:
        try:
            _sb("POST", "users",
                body={"username": username, "username_lower": username.lower(),
                      "salt": salt, "pw_hash": pw_hash, "created_at": _now()},
                prefer="return=minimal")
        except RuntimeError as e:
            if "23505" in str(e) or "duplicate" in str(e).lower():
                return False, "That username is already taken."
            raise
        return True, "ok"
    users = _read_json(_USERS, {})
    users[username] = {"salt": salt, "pw_hash": pw_hash, "created": _now()}
    _write_json(_USERS, users)
    return True, "ok"


# --------------------------------------------------------------------------
# Progress
# --------------------------------------------------------------------------
def get_progress(username):
    if USE_SUPABASE:
        rows = _sb("GET", "progress", params={"username": f"eq.{username}", "limit": 1})
        if rows:
            return {"solved": rows[0].get("solved") or {}, "attempts": rows[0].get("attempts") or {}}
        return {"solved": {}, "attempts": {}}
    return _read_json(_progress_file(username), {"solved": {}, "attempts": {}})


def save_progress(username, state):
    payload = {"username": username,
               "solved": state.get("solved", {}),
               "attempts": state.get("attempts", {})}
    if USE_SUPABASE:
        payload["updated_at"] = _now()
        _sb("POST", "progress", params={"on_conflict": "username"},
            body=payload, prefer="resolution=merge-duplicates,return=minimal")
        return
    _write_json(_progress_file(username), {"solved": payload["solved"], "attempts": payload["attempts"]})


# --------------------------------------------------------------------------
# small utils
# --------------------------------------------------------------------------
def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _progress_file(username):
    import re
    safe = re.sub(r"[^A-Za-z0-9_]", "_", username)[:60]
    return _PROGRESS / f"{safe}.json"


def _read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)
