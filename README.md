# Shri Labs

**Shridhar Infosec Solutions — CEH v13 Hands-on Labs**

A collection of self-hosted, hands-on practical labs for the CEH v13 training
programme. Each module folder is a **self-contained lab** with its own portal,
challenges, solve guides and setup scripts.

## Modules

| # | Module | What it covers | Status |
|---|--------|----------------|--------|
| 20 | [**Cryptography**](module-20-cryptography/) | Encoding, classical ciphers, encryption/decryption, hashing — 12 guided labs with a web portal, per-user accounts and per-batch flags | ✅ Ready |
| — | _more modules coming_ | | 🛠️ |

## Running a lab

Every module is standalone. For example, the cryptography lab:

```bash
cd module-20-cryptography
python3 Cryptography.py        # opens the portal at http://localhost:8000
```

Each module has its own `README.md` with full setup, tool requirements and
(for trainers) how to re-roll fresh flags per batch and share the lab over ngrok.

## Layout

```
shri-labs/
  README.md                     <- you are here (index)
  module-20-cryptography/       <- Module 20 lab (portal + challenges + generator)
  ...                           <- future module labs
```

---

© Shridhar Infosec Solutions · CEH v13 Training Programme
