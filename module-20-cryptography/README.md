# Module 20 — Cryptography CTF (Hands-on Lab)

**Shridhar Infosec Solutions · CEH v13 Training Programme**

Welcome to the practical lab for **Module 20: Cryptography**. The core ideas from
the lecture — encoding, classical ciphers, AES, RSA, hashing and the attacks
against them — you now get to *do* with real tools on real files.

This is a **capture-the-flag (CTF)** lab. Every challenge hides a flag. Find it,
submit it in the lab portal, and move on to the next one.

---

## 1. How the lab works

You run **one command** and the whole lab opens in your browser:

```bash
python3 Cryptography.py
```

Then open **http://localhost:8000** in the browser on your Kali/Ubuntu machine.

The portal gives you, for each challenge (EC-Council iLabs style):

- an **"About this lab"** explanation of the concept and why it matters,
- a clear **Objective**,
- a **step-by-step Solve Guide** with the exact commands to run,
- **Lab details** (difficulty, points, estimated time, tools) and the **files to download**,
- a **Quick hint** if you'd rather try first, and a box to **submit your flag**.

> The portal does **not** solve anything for you. You do the real work in your
> **terminal** with `openssl`, `hashcat`, `john`, `hashid`, `xxd`, etc., then bring
> the flag back to the portal. That terminal work *is* the lab.

Each trainee **signs in with their own account**, so everyone gets their own
progress and score. Your progress is saved automatically, so you can stop and come
back later.

---

## 1a. Accounts & remote access (for the trainer)

The portal has a built-in **login**. On first visit a trainee is sent to a
**Create account** page (username + password); after that they **Sign in** and see
only *their* progress.

- Accounts are stored **locally** on the machine running the portal
  (`.lab/users.json`) with **salted PBKDF2 password hashes** — passwords are never
  stored in plain text.
- Progress is per-user (`.lab/progress/<username>.json`); sessions survive a restart
  (`.lab/sessions.json`).

**Sharing the lab with a class over ngrok:**

```bash
python3 Cryptography.py            # runs on localhost:8000
ngrok http 8000                    # in another terminal
```

Give the students the `https://…ngrok…` URL. They open it, create an account, and
start solving. To wipe all accounts/progress for a fresh batch, delete the
`.lab/users.json`, `.lab/sessions.json` and `.lab/progress/` items and restart.

> This is lightweight auth for a training lab, not a production identity system.
> ngrok already gives you HTTPS; only share the URL with your class.

---

## 2. Flag format

Every flag looks like this:

```
SIS{lowercase-words-with-hyphens}
```

- Submit the **whole thing**, including `SIS{` and `}`.
- Flags are **case-sensitive**. Type them exactly.
- One flag per challenge.
- For the **Hash-Crack** challenge, the cracked password goes *inside* the braces —
  e.g. if you crack the password `sunset42`, your flag is `SIS{sunset42}`.

---

## 3. The labs

Twelve labs, grouped by topic. Every lab is **beginner / easy** (★–★★) and comes
with a **Lab Scenario** and a detailed **Solve Guide** (on the right of each lab page).

**Encoding & Decoding**
| # | Lab | Deck section | You'll use | ★ |
|---|-----|--------------|-----------|---|
| 01 | Base64 Decoding | 1 — Encoding vs Encryption | CyberChef, `base64` | ★ |
| 02 | Hex Decoding | 1 — Encoding vs Encryption | CyberChef, `xxd` | ★ |
| 03 | Binary Decoding | 1 — Encoding vs Encryption | CyberChef, python3 | ★★ |

**Classical Ciphers**
| # | Lab | Deck section | You'll use | ★ |
|---|-----|--------------|-----------|---|
| 04 | Caesar Cipher | 4 — Cryptographic Algorithms | CyberChef, python3 | ★ |
| 05 | Atbash Cipher | 4 — Cryptographic Algorithms | CyberChef, python3 | ★ |
| 06 | Vigenère Cipher (keyword given) | 4 — Cryptographic Algorithms | CyberChef, python3 | ★★ |

**Encryption & Decryption**
| # | Lab | Deck section | You'll use | ★ |
|---|-----|--------------|-----------|---|
| 07 | AES-256-CBC Decrypt (key + IV given) | 5 — Symmetric Key | `openssl` | ★★ |
| 08 | RSA Decrypt (private key given) | 6 — Asymmetric Key | `openssl` | ★★ |
| 09 | Hybrid Encryption (RSA + AES) | 6 — Asymmetric Key | `openssl` | ★★ |

**Hashing & Integrity**
| # | Lab | Deck section | You'll use | ★ |
|---|-----|--------------|-----------|---|
| 10 | Hash Crack — MD5 | 7 — Hashing | `hashid`, `hashcat`/`john` | ★★ |
| 11 | Hash Crack — SHA-1 | 7 — Hashing | `hashid`, `hashcat`/`john` | ★★ |
| 12 | Integrity Check (SHA-256) | 7 — Hashing | `sha256sum`, python3 | ★★ |

Start at **Lab 01** and work down — each lab adds one more idea or tool at a time.

---

## 4. What you need installed

The lab runs on a standard **Kali** or **Ubuntu** machine. Most of these are already
present; see [`setup/`](setup/) for a one-shot installer and a checker script.

| Tool | Needed for | Usually pre-installed? |
|------|-----------|------------------------|
| `python3` | the portal + a few challenges | ✅ Kali/Ubuntu |
| `openssl` | challenges 2, 5, 8, 9, 11 | ✅ Kali/Ubuntu |
| `base64`, `xxd`, `sha256sum` | challenges 7, 11 | ✅ (coreutils) |
| `hashid` (or `hash-identifier`) | challenges 6, 11 | ✅ Kali · install on Ubuntu |
| `hashcat` **or** `john` | challenges 6, 11 | ⚠️ install/confirm separately |
| CyberChef (optional, offline) | 1, 3, 4, 11 — a friendly GUI alternative | optional |

Run the checker any time:

```bash
bash setup/check-tools.sh
```

> **No internet needed** to *solve* any challenge. CyberChef is only an optional
> convenience — see `setup/` for how to use it offline.

---

## 5. Getting started (quick version)

```bash
# 1. from inside this folder, start the lab
python3 Cryptography.py

# 2. open http://localhost:8000 in your browser

# 3. click Challenge 01, download its file, and solve it in your terminal

# 4. submit the SIS{...} flag in the portal, then move to Challenge 02
```

If port 8000 is busy, the portal picks the next free port and prints the URL. You
can also choose one: `python3 Cryptography.py --port 8080`.

---

## 6. Rules & ethics

- Work through the challenges **in order** — each builds on the last.
- Use the **hints** before asking; they nudge, they don't solve.
- These are real offensive tools. Use them **only** on the files in this lab, or on
  systems you own or have **written permission** to test. Running `hashcat`, `john`
  or `openssl` against systems or hashes you do not own is a criminal
  offence under the IT Act and equivalent laws elsewhere. *Authorisation first — every time.*

Good hunting. When the padlock finally makes sense, this module has done its job.

*— Shridhar Infosec Solutions, CEH v13 Training*
