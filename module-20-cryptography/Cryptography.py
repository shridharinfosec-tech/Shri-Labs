#!/usr/bin/env python3
"""
SIS CEH v13 - Module 20 Cryptography - Interactive Lab Portal
=============================================================
Run this ONE file to launch the whole lab in your browser:

    python3 Cryptography.py

Then open http://localhost:8000 . The portal:
  * lists all 12 labs, grouped by topic, with progress and score
  * gives each lab a scenario, a detailed step-by-step solve guide and its files
  * checks your SIS{...} flags and tracks what you've solved

The portal never solves anything for you - do the actual work in your
Kali/Ubuntu terminal with openssl, hashcat, john, hashid, xxd, etc., then bring
the flag back here.

Dependencies: python3 standard library only.
"""

import argparse
import atexit
import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
CH = ROOT / "challenges"
LAB = ROOT / ".lab"
ASSETS = ROOT / "assets"
MANIFEST = LAB / "manifest.json"
# Runtime data (accounts / sessions / progress). Defaults to .lab for local use;
# on a hosted deploy point SIS_DATA_DIR at a persistent volume so it survives restarts.
DATA_DIR = Path(os.environ.get("SIS_DATA_DIR") or str(LAB))
USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
PROGRESS_DIR = DATA_DIR / "progress"


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------
def load_manifest():
    if not MANIFEST.exists():
        sys.exit("ERROR: .lab/manifest.json not found.\n"
                 "Generate the challenges first:\n"
                 "    python3 generator/generate_all.py")
    with open(MANIFEST) as f:
        return json.load(f)


def _read_json(path, default):
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


# --------------------------------------------------------------------------
# Accounts + sessions. Storage goes through store.py (Supabase when configured,
# local JSON files otherwise). Sessions are STATELESS signed cookies.
# --------------------------------------------------------------------------
import store  # noqa: E402  (sibling module)

USERNAME_RE = re.compile(r"^[A-Za-z0-9 ._-]{3,30}$")   # letters, numbers, space, . _ -
PW_ITERS = 200_000
SESSION_TTL = 30 * 24 * 3600   # 30 days


def _session_secret():
    s = os.environ.get("SESSION_SECRET")
    if s:
        return s.encode()
    f = LAB / ".session_secret"            # local dev: persist a random secret
    try:
        if f.exists():
            return f.read_text().strip().encode()
        val = secrets.token_hex(32)
        f.write_text(val)
        return val.encode()
    except Exception:
        return b"sis-dev-secret"


SESSION_SECRET = _session_secret()


def norm_username(u):
    return " ".join((u or "").split())   # trim ends + collapse inner whitespace


def valid_username(u):
    return bool(USERNAME_RE.match(u or ""))


def hash_pw(password, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), PW_ITERS).hex()


def create_user(username, password):
    """Validate, hash and store a new account. Returns (ok, message)."""
    if not valid_username(username):
        return False, "Username must be 3-30 characters (letters, numbers, spaces, . _ - )."
    if len(password or "") < 6:
        return False, "Password must be at least 6 characters."
    salt = secrets.token_hex(16)
    return store.create_user(username, salt, hash_pw(password, salt))


def verify_user(username, password):
    """Return the canonical stored username on success, else None."""
    rec = store.get_user(norm_username(username))
    if not rec:
        return None
    return rec["username"] if hmac.compare_digest(hash_pw(password, rec["salt"]), rec["pw_hash"]) else None


# ---- stateless signed-cookie sessions (payload.signature, HMAC-SHA256) ----
def sign_session(username):
    exp = int(time.time()) + SESSION_TTL
    payload = base64.urlsafe_b64encode(f"{username}|{exp}".encode()).decode().rstrip("=")
    sig = hmac.new(SESSION_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def session_user(token):
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    good = hmac.new(SESSION_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, good):
        return None
    try:
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
        username, exp = raw.rsplit("|", 1)
    except Exception:
        return None
    return username if int(exp) >= int(time.time()) else None


# ---- per-user progress (via store) ----
def load_state(user):
    return store.get_progress(user)


def save_state(user, state):
    store.save_progress(user, state)


MANI = load_manifest()
CHALLENGES = MANI["challenges"]
BY_ID = {c["id"]: c for c in CHALLENGES}
STATE_LOCK = threading.Lock()


def points_for(diff):
    return diff * 100


# --------------------------------------------------------------------------
# Theme - built from the Shridhar Infosec Solutions brand mark
# (navy shield + cyan glow + INFOSEC red)
# --------------------------------------------------------------------------
CSS = """
/* Palette taken directly from shridharinfosec.com brand tokens
   navy #122441 | electric red #e6244e -> #c11944 | slate #3d4d66 / #5b6b84
   light ground #f5f8fc | white panels */
:root{
  --navy:#122441; --navy-deep:#0b1a30; --navy-2:#1d3a6b;
  --red:#e6244e; --red-deep:#c11944;
  --slate:#3d4d66; --mist:#5b6b84;
  --bg:#f5f8fc; --panel:#ffffff; --white:#fff;
  --line:rgba(15,35,70,.12); --line-2:rgba(15,35,70,.20);
  --good:#129d63; --ink:#122441;
  --shadow:0 12px 30px rgba(15,35,70,.10);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;color:var(--slate);
  font:15px/1.6 "Segoe UI",-apple-system,BlinkMacSystemFont,Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);min-height:100vh}
/* faint navy dot grid, echoing the site's dotted motif */
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.5;
  background-image:radial-gradient(rgba(18,36,65,.05) 1.4px,transparent 1.4px);
  background-size:26px 26px}
a{color:var(--red-deep);text-decoration:none}
a:hover{color:var(--red)}
.wrap{max-width:1720px;margin:0 auto;padding:24px 44px 72px;position:relative;z-index:1}
@media(max-width:820px){.wrap{padding:20px 18px 60px}}

/* ---------- top nav (white, like the site) ---------- */
.nav{position:sticky;top:0;z-index:20;backdrop-filter:blur(8px);
  background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);
  box-shadow:0 2px 14px rgba(15,35,70,.05)}
.nav-inner{max-width:1720px;margin:0 auto;padding:9px 44px;display:flex;align-items:center;
  justify-content:space-between;gap:16px}
@media(max-width:820px){.nav-inner{padding:9px 18px}}
.logo-pill{display:inline-flex;align-items:center}
.logo-pill img{height:72px;display:block}
.nav-right{display:flex;align-items:center;gap:14px;flex-wrap:wrap;justify-content:flex-end}
.nav-title{color:var(--navy);font-size:17px;font-weight:700;letter-spacing:.2px}
.batch{font:700 11px/1 "Segoe UI";letter-spacing:1.2px;color:#fff;
  background:linear-gradient(135deg,var(--red),var(--red-deep));padding:6px 12px;border-radius:20px}

/* ---------- hero (clean dark navy, brand watermark) ---------- */
.hero{margin:22px 0 20px;padding:32px 36px 28px;border-radius:14px;position:relative;overflow:hidden;color:#eaf1fb;
  background:linear-gradient(180deg,#15294b,#0e1e37);border:1px solid rgba(255,255,255,.06);
  box-shadow:0 14px 34px rgba(11,26,48,.18)}
.hero::after{content:"";position:absolute;right:36px;top:50%;transform:translateY(-50%);
  width:210px;height:210px;opacity:.06;pointer-events:none;
  background:url('/assets/shield.png') center/contain no-repeat}
.eyebrow{position:relative;display:inline-flex;align-items:center;gap:9px;color:#93a8ca;font-weight:700;
  font-size:11px;letter-spacing:2.6px;text-transform:uppercase}
.eyebrow svg{color:var(--red)}
.hero h1{position:relative;margin:12px 0 9px;font-size:31px;letter-spacing:.1px;color:#fff;font-weight:800}
.hero p{position:relative;margin:0;color:#aebfd8;max-width:690px;font-size:14.5px;line-height:1.68}
.hero p code{color:#ffd3db}
.hero-auth{position:relative;margin-top:16px;display:inline-flex;align-items:center;gap:7px;
  color:#8296b5;font-size:12px}
.hero-auth svg{color:#6f86a8}

/* ---------- stats ---------- */
.stats{position:relative;display:flex;gap:0;align-items:center;flex-wrap:wrap;margin-top:24px;
  padding-top:22px;border-top:1px solid rgba(255,255,255,.10)}
.ring{--p:0;width:74px;height:74px;border-radius:50%;flex:0 0 auto;margin-right:26px;
  background:conic-gradient(var(--red) calc(var(--p)*1%), rgba(255,255,255,.12) 0);
  display:flex;align-items:center;justify-content:center}
.ring .hole{width:56px;height:56px;border-radius:50%;background:#0e1e37;
  display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1;color:#fff}
.ring .hole b{font-size:17px} .ring .hole span{font-size:8.5px;color:#8ea3c2;letter-spacing:.5px}
.stat{min-width:104px;padding:2px 26px;border-left:1px solid rgba(255,255,255,.10)}
.stat b{display:block;font-size:21px;color:#fff;font-weight:800}
.stat span{color:#8ea3c2;font-size:10.5px;text-transform:uppercase;letter-spacing:.9px}
.stat.spacer{flex:1;border:0;min-width:0;padding:0}

/* ---------- challenge grid ---------- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
.cat-h{display:flex;align-items:center;gap:10px;margin:28px 0 12px;font-size:14px;font-weight:800;
  letter-spacing:.7px;text-transform:uppercase;color:var(--navy)}
.cat-h .dot{width:9px;height:9px;border-radius:50%;flex:0 0 auto;
  background:linear-gradient(135deg,var(--red),var(--red-deep))}
.cat-h .cat-count{margin-left:auto;font-size:11.5px;font-weight:700;color:var(--mist);
  background:#eef3fa;border:1px solid var(--line);padding:3px 10px;border-radius:20px;
  letter-spacing:.3px;text-transform:none}
.card{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:17px 17px 15px;color:inherit;
  display:flex;flex-direction:column;gap:9px;box-shadow:0 4px 14px rgba(15,35,70,.05);
  transition:transform .08s,border-color .15s,box-shadow .15s}
.card:hover{transform:translateY(-3px);border-color:rgba(230,36,78,.35);box-shadow:0 14px 30px rgba(15,35,70,.14)}
.card.done{border-color:rgba(18,157,99,.45)}
.card-top{display:flex;justify-content:space-between;align-items:center;gap:10px}
.cnum{font:800 12px/1 Consolas,monospace;letter-spacing:1.5px;color:#fff;
  background:var(--navy);padding:6px 10px;border-radius:7px}
.cnum.b{background:linear-gradient(135deg,var(--red),var(--red-deep))}
.badge{font:700 10.5px/1 "Segoe UI";letter-spacing:.8px;text-transform:uppercase;padding:5px 10px;border-radius:20px;
  border:1px solid var(--line-2);color:var(--mist);display:inline-flex;align-items:center;gap:5px}
.badge.solved{color:#fff;background:var(--good);border-color:var(--good)}
.card h3{margin:2px 0 0;font-size:16.5px;line-height:1.3;color:var(--navy)}
.csec{color:var(--mist);font-size:12px}
.cmeta{display:flex;align-items:center;gap:10px;margin-top:1px}
.stars{color:var(--red);font-size:12px;letter-spacing:1px}
.pts{color:var(--mist);font-size:11.5px;font-weight:700}
.cbrief{color:var(--slate);font-size:13.3px;flex:1}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:2px}
.chip{font:600 11px/1 "Segoe UI";color:var(--navy-2);background:#eef3fa;
  border:1px solid var(--line);padding:4px 9px;border-radius:6px}

/* ---------- detail page ---------- */
.crumbs{color:var(--mist);font-size:12.5px;margin:6px 0 2px}
.crumbs a{color:var(--slate)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:24px;margin:14px 0;box-shadow:var(--shadow)}
.detail{display:grid;grid-template-columns:0.92fr 1.85fr;gap:16px;align-items:start;margin:14px 0}
.detail .panel{margin:0}
@media(max-width:920px){.detail{grid-template-columns:1fr}}
.manual{padding:26px 34px 30px}
.manual .scenario{margin-bottom:6px}
.aside{position:sticky;top:80px}
.aside h4{margin:16px 0 6px;font-size:14px;color:var(--navy);text-transform:uppercase;letter-spacing:.5px}
.aside h4:first-child{margin-top:0}
.sec-h{font-size:16px;color:var(--navy);margin:26px 0 10px;font-weight:700;
  display:flex;align-items:center;gap:8px}
.manual .phead + .detail-sec{margin-bottom:6px}
.sec-h .ic{color:var(--red)}
.scenario{color:var(--slate);font-size:14.5px;line-height:1.72;margin:6px 0 2px}
.objbox{background:#f0f4fa;border:1px solid var(--line);border-left:3px solid var(--red);border-radius:8px;
  padding:12px 14px;color:var(--navy);font-size:13.6px;line-height:1.6;margin:0 0 4px}
.ob-label{display:block;font-size:10.5px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;
  color:var(--red-deep);margin-bottom:5px}
.steps{margin-top:4px}
.step{display:flex;gap:14px;padding:18px 0 20px}
.step + .step{border-top:1px solid var(--line)}
.step .no{flex:0 0 auto;width:26px;height:26px;border-radius:50%;background:var(--navy);color:#fff;
  font:700 13px/26px Consolas,monospace;text-align:center}
.step .sbody{flex:1;min-width:0}
.step .st{font-weight:700;color:var(--navy);font-size:14.5px}
.step .sd{margin:5px 0 0;font-size:13.5px;color:var(--slate);line-height:1.6}
.step pre{margin-top:11px;padding:11px 15px;font-size:12.5px}
.labmeta{list-style:none;padding:0;margin:0}
.labmeta li{display:flex;justify-content:space-between;gap:10px;padding:7px 0;
  border-bottom:1px solid var(--line);font-size:13px}
.labmeta li:last-child{border-bottom:0}
.labmeta .k{color:var(--mist)} .labmeta .v{color:var(--navy);font-weight:600;text-align:right}
.phead{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.phead h2{margin:0;font-size:23px;color:var(--navy)}
.detail-sec{color:var(--mist);font-size:13px;margin-top:4px}
.kv{color:var(--slate);font-size:13px}
.kv b,.phead h2 b{color:var(--navy)}
.files a{display:inline-flex;align-items:center;gap:8px;background:#eef3fa;border:1px solid var(--line);
  padding:9px 13px;border-radius:9px;margin:5px 7px 0 0;font-size:13px;color:var(--navy);font-weight:600}
.files a:hover{border-color:var(--red);color:var(--red-deep)}
.files svg{opacity:.85}
pre{background:var(--navy-deep);border:1px solid var(--navy);border-radius:11px;padding:13px 15px;overflow:auto;
  font:12.5px/1.55 Consolas,Monaco,monospace;color:#cfe0f5;white-space:pre-wrap;margin:0}
details{background:#f0f4fa;border:1px solid var(--line);border-radius:11px;padding:12px 15px;margin-top:10px}
summary{cursor:pointer;color:var(--red-deep);font-weight:700;font-size:13.5px;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"\\25B8  "}
details[open] summary::before{content:"\\25BE  "}
details pre{margin-top:10px}
input[type=text],textarea{width:100%;background:#fff;border:1px solid var(--line-2);border-radius:10px;
  color:var(--navy);padding:12px 13px;font:14px Consolas,monospace}
input[type=text]:focus,textarea:focus{outline:none;border-color:var(--red);box-shadow:0 0 0 3px rgba(230,36,78,.14)}
textarea{min-height:160px;font-family:inherit}
.row{display:flex;gap:11px;margin-top:12px;flex-wrap:wrap;align-items:center}
.btn{display:inline-flex;align-items:center;gap:8px;border:0;cursor:pointer;font:700 14px "Segoe UI";
  padding:11px 20px;border-radius:10px;color:#fff;
  background:linear-gradient(135deg,var(--red),var(--red-deep));transition:filter .12s,transform .05s}
.btn:hover{filter:brightness(1.06)} .btn:active{transform:translateY(1px)}
.btn.ghost{background:transparent;color:var(--navy);border:1px solid var(--line-2)}
.btn.ghost:hover{border-color:var(--red);color:var(--red-deep)}
.back{color:var(--mist);font-size:13px}

/* ---------- callouts / banners ---------- */
.msg{padding:12px 15px;border-radius:11px;margin:14px 0;font-weight:600;display:flex;align-items:center;gap:9px}
.msg.ok{background:rgba(18,157,99,.10);border:1px solid rgba(18,157,99,.45);color:#0c7a4d}
.msg.bad{background:rgba(230,36,78,.09);border:1px solid rgba(230,36,78,.40);color:var(--red-deep)}
.msg.info{background:rgba(29,58,107,.07);border:1px solid rgba(29,58,107,.30);color:var(--navy-2)}
.msg code{background:rgba(18,36,65,.06);border-color:var(--line)}
code{background:rgba(18,36,65,.06);border:1px solid var(--line);padding:1px 6px;border-radius:5px;
  font:12.5px Consolas,monospace;color:var(--navy)}

/* ---------- auth (login / register) ---------- */
.auth-wrap{max-width:426px;margin:5vh auto 0;padding:0 8px}
.auth-card{background:var(--panel);border:1px solid var(--line);border-radius:16px;
  padding:30px 30px 26px;box-shadow:var(--shadow)}
.auth-card h2{margin:0 0 4px;color:var(--navy);font-size:23px}
.auth-sub{margin:0 0 6px;color:var(--mist);font-size:13.5px}
.auth-card label{display:block;margin:15px 0 5px;color:var(--navy);font-weight:600;font-size:13px}
.auth-card .hintlabel{color:var(--mist);font-weight:400;font-size:11.5px}
.auth-card input{width:100%;background:#fff;border:1px solid var(--line-2);border-radius:10px;
  color:var(--navy);padding:11px 12px;font:14px "Segoe UI",Arial,sans-serif}
.auth-card input:focus{outline:none;border-color:var(--red);box-shadow:0 0 0 3px rgba(230,36,78,.14)}
.auth-alt{margin:18px 0 0;text-align:center;color:var(--mist);font-size:13px}
.nav-user{display:inline-flex;align-items:center;gap:12px;margin-left:6px;padding-left:14px;
  border-left:1px solid var(--line)}
.nav-uname{color:var(--navy);font-weight:700;font-size:13.5px}
.nav-logout{background:transparent;border:1px solid var(--line-2);color:var(--navy);
  font:600 12.5px "Segoe UI";padding:6px 13px;border-radius:8px;cursor:pointer}
.nav-logout:hover{border-color:var(--red);color:var(--red-deep)}

/* ---------- confirmation modal ---------- */
.modal-overlay{position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;
  background:rgba(11,26,48,.55);backdrop-filter:blur(3px);padding:20px;animation:fade .12s ease}
.modal-overlay[hidden]{display:none}
@keyframes fade{from{opacity:0}to{opacity:1}}
.modal{background:#fff;border:1px solid var(--line);border-radius:16px;max-width:430px;width:100%;
  padding:26px 26px 22px;box-shadow:0 24px 60px rgba(15,35,70,.35);text-align:center}
.modal .m-ic{width:48px;height:48px;border-radius:50%;margin:0 auto 14px;display:flex;align-items:center;justify-content:center;
  background:rgba(230,36,78,.12);color:var(--red-deep)}
.modal h3{margin:0 0 8px;color:var(--navy);font-size:19px}
.modal p{margin:0 0 20px;color:var(--slate);font-size:14px;line-height:1.6}
.modal p b{color:var(--navy)}
.modal-actions{display:flex;gap:10px;justify-content:center}
.modal-actions .btn{min-width:120px;justify-content:center}
.modal-actions form{display:inline}

/* ---------- footer ---------- */
.foot{border-top:1px solid var(--line);margin-top:36px;background:#fff}
.foot-inner{max-width:1720px;margin:0 auto;padding:22px 44px;display:flex;gap:16px;align-items:center;
  justify-content:space-between;flex-wrap:wrap;color:var(--mist);font-size:12px}
@media(max-width:820px){.foot-inner{padding:22px 18px}}
.foot .logo-pill img{height:26px}
.foot .fnote{line-height:1.7}
.foot b{color:var(--navy)}
"""

ICON_DL = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
           '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>')
ICON_CHECK = ('<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>')
ICON_SHIELD = ('<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
               'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>')
ICON_RESET = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              '<polyline points="1 4 1 10 7 10"/>'
              '<path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>')
ICON_STEPS = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>'
              '<line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/>'
              '<line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>')


def _shell(title, nav_html, body):
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="icon" type="image/png" href="/assets/favicon.png">
<style>{CSS}</style></head>
<body>
{nav_html}
<div class="wrap">
{body}
</div>
<script>
function sisModal(id, show){{var m=document.getElementById(id); if(m) m.hidden=!show;}}
document.addEventListener('keydown', function(e){{
  if(e.key==='Escape') document.querySelectorAll('.modal-overlay').forEach(function(m){{m.hidden=true;}});
}});
</script>
</body></html>"""


def page(title, body, user=None):
    userbox = ""
    if user:
        userbox = (f'<span class="nav-user"><span class="nav-uname">{html.escape(user)}</span>'
                   f'<form method="post" action="/logout" style="display:inline">'
                   f'<button class="nav-logout" type="submit">Logout</button></form></span>')
    nav = f"""<header class="nav"><div class="nav-inner">
  <a href="/" class="logo-pill" title="Shridhar Infosec Solutions">
    <img src="/assets/sis-logo.png" alt="Shridhar Infosec Solutions"></a>
  <div class="nav-right">
    <span class="nav-title">CEH&nbsp;v13 &middot; Module&nbsp;20 &middot; Cryptography Lab</span>
    {userbox}
  </div>
</div></header>"""
    return _shell(title, nav, body)


def auth_page(title, body):
    """Minimal centered shell for the login / register screens (logo only, no nav)."""
    nav = ('<header class="nav"><div class="nav-inner" style="justify-content:center">'
           '<span class="logo-pill"><img src="/assets/sis-logo.png" alt="Shridhar Infosec Solutions"></span>'
           '</div></header>')
    return _shell(title, nav, f'<div class="auth-wrap">{body}</div>')


def login_page(msg="", username=""):
    err = f'<div class="msg bad">{html.escape(msg)}</div>' if msg else ""
    body = f"""
    <div class="auth-card">
      <h2>Sign in</h2>
      <p class="auth-sub">Access your Module 20 cryptography labs.</p>
      {err}
      <form method="post" action="/login">
        <label>Username</label>
        <input type="text" name="username" value="{html.escape(username)}" autocomplete="username" autofocus>
        <label>Password</label>
        <input type="password" name="password" autocomplete="current-password">
        <button class="btn" type="submit" style="width:100%;margin-top:18px;justify-content:center">Sign in</button>
      </form>
      <p class="auth-alt">New here? <a href="/register">Create an account</a></p>
    </div>"""
    return auth_page("Sign in - SIS Cryptography Lab", body)


def register_page(msg="", username=""):
    err = f'<div class="msg bad">{html.escape(msg)}</div>' if msg else ""
    body = f"""
    <div class="auth-card">
      <h2>Create your account</h2>
      <p class="auth-sub">Pick a username and password to track your lab progress.</p>
      {err}
      <form method="post" action="/register">
        <label>Username <span class="hintlabel">(3&ndash;30 chars: letters, numbers, spaces)</span></label>
        <input type="text" name="username" value="{html.escape(username)}" autocomplete="username" autofocus>
        <label>Password <span class="hintlabel">(min 6 characters)</span></label>
        <input type="password" name="password" autocomplete="new-password">
        <label>Confirm password</label>
        <input type="password" name="confirm" autocomplete="new-password">
        <button class="btn" type="submit" style="width:100%;margin-top:18px;justify-content:center">Create account</button>
      </form>
      <p class="auth-alt">Already have an account? <a href="/login">Sign in</a></p>
    </div>"""
    return auth_page("Create account - SIS Cryptography Lab", body)


def stars(n):
    return "★" * n + "☆" * (5 - n)


def stars_html(n):
    return (f'<span style="color:var(--red)">{"★" * n}</span>'
            f'<span style="color:#c3cede">{"☆" * (5 - n)}</span>')


def level_word(n):
    return "Beginner" if n <= 1 else "Easy" if n == 2 else "Medium" if n == 3 else "Advanced"


def dashboard(user, state, banner=""):
    solved = state["solved"]
    core = [c for c in CHALLENGES if c["id"] != "bonus"]
    total_pts = sum(points_for(c["difficulty"]) for c in core)
    got_pts = sum(points_for(c["difficulty"]) for c in core if c["id"] in solved)
    nsolved = len([c for c in core if c["id"] in solved])
    pct = int(round(100 * nsolved / len(core))) if core else 0
    bonus_done = "bonus" in solved
    has_bonus = "bonus" in BY_ID
    bonus_stat = (f'<div class="stat"><b style="color:{"var(--good)" if bonus_done else "var(--dim)"}">'
                  f'{"✓" if bonus_done else "—"}</b><span>Bonus</span></div>') if has_bonus else ""

    def card_html(c):
        cid = c["id"]
        done = cid in solved
        is_bonus = cid == "bonus"
        badge = (f'<span class="badge solved">{ICON_CHECK} Solved</span>' if done
                 else '<span class="badge">Open</span>')
        cnum = "BONUS" if is_bonus else cid
        cls = "cnum b" if is_bonus else "cnum"
        chips = "".join(f'<span class="chip">{html.escape(t)}</span>' for t in c["tools"])
        pts = "bonus" if is_bonus else f'{points_for(c["difficulty"])} pts'
        return f"""
        <a class="card {'done' if done else ''}" href="/c/{cid}">
          <div class="card-top"><span class="{cls}">{cnum}</span>{badge}</div>
          <h3>{html.escape(c['title'])}</h3>
          <div class="csec">{html.escape(c['section'])}</div>
          <div class="cmeta"><span class="stars">{stars_html(c['difficulty'])}</span><span class="pts">{pts}</span></div>
          <p class="cbrief">{html.escape(c['brief'])}</p>
          <div class="chips">{chips}</div>
        </a>"""

    # group challenges under their topic category (manifest order)
    cats = MANI.get("categories") or []
    seen_cats = []
    for c in CHALLENGES:
        cat = c.get("category", "Challenges")
        if cat not in cats and cat not in seen_cats:
            seen_cats.append(cat)
    ordered_cats = cats + seen_cats

    sections = []
    for cat in ordered_cats:
        members = [c for c in CHALLENGES if c.get("category", "Challenges") == cat]
        if not members:
            continue
        done_n = len([c for c in members if c["id"] in solved])
        cards = "".join(card_html(c) for c in members)
        sections.append(f"""
        <div class="cat-h"><span class="dot"></span>{html.escape(cat)}
          <span class="cat-count">{done_n}/{len(members)}</span></div>
        <div class="grid">{cards}</div>""")

    body = f"""
    {banner}
    <section class="hero">
      <span class="eyebrow">{ICON_SHIELD} Module 20 &middot; Hands-on Lab</span>
      <h1>Applied Cryptography Lab</h1>
      <p>Twelve guided labs across encoding, classical ciphers, encryption and hashing. Each lab
      has a scenario and a step-by-step solve guide &mdash; do the work in your Kali terminal, then
      submit the <code>SIS{{...}}</code> flag to record your progress.</p>
      <div class="hero-auth">{ICON_SHIELD} Authorised training environment &middot; localhost only</div>
      <div class="stats">
        <div class="ring" style="--p:{pct}"><div class="hole"><b>{pct}%</b><span>DONE</span></div></div>
        <div class="stat"><b>{nsolved}<span style="color:#6f86a8">/{len(core)}</span></b><span>Labs</span></div>
        <div class="stat"><b>{got_pts}<span style="color:#6f86a8">/{total_pts}</span></b><span>Points</span></div>
        {bonus_stat}
        <div class="stat spacer"></div>
      </div>
    </section>
    {''.join(sections)}
    <div class="row" style="margin-top:24px">
      <button type="button" class="btn ghost" onclick="sisModal('m-reset-all',true)">Reset all progress</button>
    </div>
    <div id="m-reset-all" class="modal-overlay" hidden onclick="if(event.target===this)this.hidden=true">
      <div class="modal">
        <div class="m-ic">{ICON_RESET}</div>
        <h3>Reset all progress?</h3>
        <p>Every lab's solved status and attempts will be cleared. This cannot be undone.</p>
        <div class="modal-actions">
          <button type="button" class="btn ghost" onclick="sisModal('m-reset-all',false)">Cancel</button>
          <form method="post" action="/reset"><button class="btn" type="submit">Reset all</button></form>
        </div>
      </div>
    </div>
    """
    return page("Module 20 Cryptography Lab", body, user=user)


def render_steps(steps):
    out = []
    for i, s in enumerate(steps, 1):
        cmd = f'<pre>{html.escape(s.get("cmd",""))}</pre>' if s.get("cmd") else ""
        out.append(
            f'<div class="step"><div class="no">{i}</div><div class="sbody">'
            f'<div class="st">{html.escape(s.get("title",""))}</div>'
            f'<div class="sd">{html.escape(s.get("desc",""))}</div>{cmd}</div></div>')
    return "".join(out)


def challenge_page(cid, user, state, banner=""):
    c = BY_ID[cid]
    is_solved = cid in state["solved"]
    attempts = state["attempts"].get(cid, 0)

    files = "".join(f'<a href="/dl/{cid}/{html.escape(fn)}">{ICON_DL} {html.escape(fn)}</a>'
                    for fn in c["files"])
    hint = html.escape(c.get("hint", "")).strip()
    solved_banner = (f'<div class="msg ok">{ICON_CHECK} You solved this lab.</div>' if is_solved else "")

    scenario = html.escape(c.get("scenario", "")).strip() or html.escape(c["brief"])
    objective = html.escape(c.get("objective", "")).strip() or html.escape(c["brief"])
    steps_html = render_steps(c.get("steps", []))
    tools_v = ", ".join(html.escape(t) for t in c["tools"])

    # per-lab reset (always available) + its confirmation modal
    reset_ui = (f'<button type="button" class="btn ghost" style="width:100%;margin-top:14px" '
                f'onclick="sisModal(\'m-reset-lab\',true)">Reset this lab</button>')
    reset_modal = f"""
    <div id="m-reset-lab" class="modal-overlay" hidden onclick="if(event.target===this)this.hidden=true">
      <div class="modal">
        <div class="m-ic">{ICON_RESET}</div>
        <h3>Reset this lab?</h3>
        <p>Your progress for <b>Lab {cid} &mdash; {html.escape(c['title'])}</b> (solved status and
        attempts) will be cleared, so you can start it fresh.</p>
        <div class="modal-actions">
          <button type="button" class="btn ghost" onclick="sisModal('m-reset-lab',false)">Cancel</button>
          <form method="post" action="/reset-lab"><input type="hidden" name="id" value="{cid}">
            <button class="btn" type="submit">Reset lab</button></form>
        </div>
      </div>
    </div>"""

    # LEFT column: objective, lab details, files, submit (sticky)
    left = f"""
      <div class="objbox"><span class="ob-label">Objective</span>{objective}</div>
      <h4>Lab details</h4>
      <ul class="labmeta">
        <li><span class="k">Track</span><span class="v">{html.escape(c.get('category',''))}</span></li>
        <li><span class="k">Level</span><span class="v">{stars_html(c['difficulty'])} &nbsp;{level_word(c['difficulty'])}</span></li>
        <li><span class="k">Points</span><span class="v">{points_for(c['difficulty'])}</span></li>
        <li><span class="k">Est. time</span><span class="v">{html.escape(c.get('est_time','—'))}</span></li>
        <li><span class="k">Tools</span><span class="v">{tools_v}</span></li>
      </ul>
      <h4>Lab files</h4>
      <div class="files">{files or '<span class="kv">no downloadable files</span>'}</div>
      <h4>Submit flag</h4>
      <form method="post" action="/submit">
        <input type="hidden" name="id" value="{cid}">
        <p class="kv" style="margin:2px 0 8px">Format <code>SIS{{...}}</code></p>
        <input type="text" name="flag" placeholder="SIS{{...}}" autocomplete="off" spellcheck="false">
        <div class="row"><button class="btn" type="submit">Submit flag</button></div>
        <p class="pts" style="margin-top:10px">attempts: {attempts}</p>
      </form>
      {reset_ui}"""

    # RIGHT column: the detailed lab manual (scenario + step-by-step guide)
    right = f"""
      <div class="phead">
        <span class="cnum">{cid}</span>
        <h2>{html.escape(c['title'])}</h2>
      </div>
      <div class="detail-sec">{html.escape(c.get('category',''))} &nbsp;&middot;&nbsp; {html.escape(c['section'])}</div>
      <div class="sec-h">{ICON_SHIELD}<span>Lab Scenario</span></div>
      <p class="scenario">{scenario}</p>
      <div class="sec-h"><span class="ic">{ICON_STEPS}</span><span>Solve Guide</span></div>
      <div class="steps">{steps_html}</div>
      <details style="margin-top:14px"><summary>Quick hint (one-line nudge)</summary><pre>{hint}</pre></details>"""

    body = f"""
    {banner}{solved_banner}
    <div class="crumbs"><a href="/">All labs</a> &nbsp;/&nbsp; {html.escape(c.get('category',''))} &nbsp;/&nbsp; Lab {cid}</div>
    <div class="detail">
      <div class="panel aside">{left}</div>
      <div class="panel manual">{right}</div>
    </div>
    <p style="margin-top:14px"><a class="back" href="/">&larr; back to all labs</a></p>
    {reset_modal}
    """
    return page(f"Lab {cid} - {c['title']}", body, user=user)


# --------------------------------------------------------------------------
# Flag / bonus checking
# --------------------------------------------------------------------------
def check_flag(cid, submitted):
    c = BY_ID.get(cid)
    if not c:
        return False
    salt = bytes.fromhex(MANI["salt"])
    iters = MANI.get("pbkdf2_iters", 100_000)
    guess = hashlib.pbkdf2_hmac("sha256", submitted.strip().encode(), salt, iters).hex()
    return hmac.compare_digest(guess, c["flag_pbkdf2"])


def _bonus_keywords():
    c = BY_ID.get("bonus")
    if not c:
        return []
    return [base64.b64decode(b).decode() for b in c.get("issue_keywords_b64", [])]


def check_bonus(notes):
    kws = _bonus_keywords()
    c = BY_ID["bonus"]
    threshold = c.get("issue_threshold", 5)
    norm = "".join(ch.lower() if ch.isalnum() else " " for ch in notes)
    compact = norm.replace(" ", "")
    hits = sorted({k for k in kws if k in compact})
    return len(hits) >= threshold, len(hits), threshold


def bonus_flag_text():
    """Decrypt the bonus flag (locked with the keyword set) for on-success display."""
    enc = LAB / "bonus.enc"
    if not enc.exists():
        return "SIS{...}  (bonus.enc missing - re-run the generator)"
    km = hashlib.sha256("|".join(sorted(_bonus_keywords())).encode()).digest()
    ct = bytes.fromhex(enc.read_text().strip())
    out, i = b"", 0
    while len(out) < len(ct):
        out += hashlib.sha256(km + i.to_bytes(4, "big")).digest()
        i += 1
    return bytes(a ^ b for a, b in zip(ct, out[:len(ct)])).decode(errors="replace")


# --------------------------------------------------------------------------
# HTTP handler
# --------------------------------------------------------------------------
CTYPES = {".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon",
          ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".css": "text/css"}


class Handler(BaseHTTPRequestHandler):
    server_version = "SIS-CTF/2.0"

    def log_message(self, *a):
        pass

    def _send(self, body, code=200, ctype="text/html; charset=utf-8", headers=None):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, loc, cookie=None):
        self.send_response(303)
        self.send_header("Location", loc)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _current(self):
        """(username, token) from the session cookie, or (None, None)."""
        raw = self.headers.get("Cookie", "")
        try:
            c = SimpleCookie(raw)
            tok = c["sis_session"].value if "sis_session" in c else None
        except Exception:
            tok = None
        return session_user(tok), tok

    def do_GET(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p != ""]
        q = parse_qs(u.query)

        # ---- always-public ----
        if u.path in ("/favicon.ico", "/favicon.png"):
            return self._asset("favicon.png")
        if parts and parts[0] == "assets" and len(parts) == 2:
            return self._asset(parts[1])
        if u.path == "/health":
            return self._send("ok", ctype="text/plain")

        user, _ = self._current()

        # ---- auth screens ----
        if u.path == "/login":
            return self._redirect("/") if user else self._send(login_page())
        if u.path == "/register":
            return self._redirect("/") if user else self._send(register_page())

        # ---- everything else needs a login ----
        if not user:
            return self._redirect("/login")

        with STATE_LOCK:
            state = load_state(user)
        if not parts:
            return self._send(dashboard(user, state, self._banner(q)))
        if parts[0] == "c" and len(parts) == 2 and parts[1] in BY_ID:
            return self._send(challenge_page(parts[1], user, state, self._banner(q)))
        if parts[0] == "dl" and len(parts) == 3:
            return self._download(parts[1], parts[2])
        return self._send(page("Not found", '<div class="msg bad">Not found.</div><a href="/">&larr; home</a>',
                               user=user), code=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode(errors="replace") if length else ""
        form = parse_qs(raw)
        u = urlparse(self.path)
        setcookie = "sis_session={}; Path=/; HttpOnly; SameSite=Lax"

        # ---- auth endpoints (public) ----
        if u.path == "/login":
            username = norm_username(form.get("username", [""])[0])
            password = form.get("password", [""])[0]
            key = verify_user(username, password)
            if key:
                return self._redirect("/", cookie=setcookie.format(sign_session(key)))
            return self._send(login_page("Invalid username or password.", username))

        if u.path == "/register":
            username = norm_username(form.get("username", [""])[0])
            password = form.get("password", [""])[0]
            confirm = form.get("confirm", [""])[0]
            if password != confirm:
                return self._send(register_page("The two passwords do not match.", username))
            ok, msg = create_user(username, password)
            if not ok:
                return self._send(register_page(msg, username))
            return self._redirect("/", cookie=setcookie.format(sign_session(username)))

        if u.path == "/logout":
            return self._redirect("/login", cookie="sis_session=; Path=/; Max-Age=0")

        # ---- everything else needs a login ----
        user, _ = self._current()
        if not user:
            return self._redirect("/login")

        if u.path == "/submit":
            cid = form.get("id", [""])[0]
            flag = form.get("flag", [""])[0]
            if cid not in BY_ID:
                return self._redirect("/")
            with STATE_LOCK:
                state = load_state(user)
                state["attempts"][cid] = state["attempts"].get(cid, 0) + 1
                if check_flag(cid, flag):
                    state["solved"].setdefault(cid, time.strftime("%Y-%m-%d %H:%M:%S"))
                    save_state(user, state)
                    return self._redirect(f"/c/{cid}?m=ok")
                save_state(user, state)
                return self._redirect(f"/c/{cid}?m=bad")

        if u.path == "/reset-lab":
            cid = form.get("id", [""])[0]
            if cid in BY_ID:
                with STATE_LOCK:
                    state = load_state(user)
                    state["solved"].pop(cid, None)
                    state["attempts"].pop(cid, None)
                    save_state(user, state)
                return self._redirect(f"/c/{cid}?m=labreset")
            return self._redirect("/")

        if u.path == "/reset":
            with STATE_LOCK:
                save_state(user, {"solved": {}, "attempts": {}})
            return self._redirect("/?m=reset")

        return self._redirect("/")

    def _banner(self, q):
        m = q.get("m", [""])[0]
        if m == "ok":
            return f'<div class="msg ok">{ICON_CHECK} Correct flag &mdash; challenge solved!</div>'
        if m == "bad":
            return '<div class="msg bad">&#10007; Not quite. Check your flag and try again.</div>'
        if m == "reset":
            return '<div class="msg info">All progress reset.</div>'
        if m == "labreset":
            return '<div class="msg info">This lab has been reset &mdash; you can solve it again.</div>'
        if m == "bonusok":
            return f'<div class="msg ok">{ICON_CHECK} Bonus earned! Flag: <code>{html.escape(bonus_flag_text())}</code></div>'
        if m == "bonusno":
            h = q.get("h", ["0"])[0]
            n = q.get("n", ["5"])[0]
            return f'<div class="msg bad">Not enough yet &mdash; you identified {h} of the {n} issues needed. Add more distinct mistakes and their fixes.</div>'
        return ""

    def _download(self, cid, filename):
        c = BY_ID.get(cid)
        if not c or filename not in c["files"]:
            return self._send("forbidden", code=403, ctype="text/plain")
        path = CH / c["slug"] / filename
        if not path.exists() or not path.is_file():
            return self._send("not found", code=404, ctype="text/plain")
        self._send(path.read_bytes(), ctype="application/octet-stream",
                   headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    def _asset(self, name):
        # serve only real files that live directly in assets/
        if "/" in name or "\\" in name or name.startswith("."):
            return self._send("forbidden", code=403, ctype="text/plain")
        path = ASSETS / name
        if not path.exists() or not path.is_file():
            return self._send("not found", code=404, ctype="text/plain")
        ctype = CTYPES.get(path.suffix.lower(), "application/octet-stream")
        self._send(path.read_bytes(), ctype=ctype,
                   headers={"Cache-Control": "max-age=86400"})


# --------------------------------------------------------------------------
# TLS server for Challenge 9
# --------------------------------------------------------------------------
_tls_proc = None


def start_tls_server():
    global _tls_proc
    c = next((c for c in CHALLENGES if c.get("tls_server")), None)
    if not c:
        return
    port = c.get("tls_port", 4443)
    srv_dir = CH / c["slug"] / c["tls_server"]
    cert = srv_dir / "server.pem"
    key = srv_dir / "server.key"
    chain = srv_dir / "chain.pem"
    ossl = shutil.which("openssl")
    if not ossl:
        print("  [!] openssl not found - Challenge 9 TLS server NOT started (install openssl).")
        return
    if not cert.exists() or not key.exists():
        print("  [!] Challenge 9 server cert/key missing - run the generator.")
        return
    if _port_in_use(port):
        print(f"  [i] Port {port} already in use - assuming Challenge 9 server is up.")
        return
    cmd = [ossl, "s_server", "-accept", str(port), "-cert", str(cert), "-key", str(key)]
    if chain.exists():
        cmd += ["-cert_chain", str(chain)]
    cmd += ["-www", "-quiet"]
    try:
        _tls_proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(srv_dir))
        time.sleep(0.6)
        print(f"  [+] Challenge 9 TLS server on localhost:{port} (broken chain, on purpose)")
    except Exception as e:
        print(f"  [!] Could not start Challenge 9 TLS server: {e}")


def stop_tls_server():
    global _tls_proc
    if _tls_proc and _tls_proc.poll() is None:
        _tls_proc.terminate()
        try:
            _tls_proc.wait(timeout=4)
        except Exception:
            _tls_proc.kill()


def _port_in_use(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="SIS Module 20 Cryptography CTF portal")
    ap.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8000, help="portal port (default 8000)")
    ap.add_argument("--no-tls", action="store_true", help="do not start the Challenge 9 TLS server")
    args = ap.parse_args()

    port = args.port
    for _ in range(20):
        if not _port_in_use(port, args.host):
            break
        port += 1

    print("=" * 66)
    print("  SHRIDHAR INFOSEC SOLUTIONS  -  CEH v13")
    print("  Module 20: Cryptography  -  Interactive CTF Lab")
    print("=" * 66)
    if not args.no_tls:
        start_tls_server()
        atexit.register(stop_tls_server)
    httpd = ThreadingHTTPServer((args.host, port), Handler)
    shown = "localhost" if args.host in ("127.0.0.1", "0.0.0.0") else args.host
    print(f"  [+] Lab portal ready:  http://{shown}:{port}")
    print(f"  [+] Open that in your browser. Press Ctrl+C to stop.")
    print("=" * 66)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down. Good hunting!")
    finally:
        stop_tls_server()
        httpd.server_close()


if __name__ == "__main__":
    main()
