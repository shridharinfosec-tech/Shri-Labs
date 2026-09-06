# Setup

The lab targets a standard **Kali** or **Ubuntu/Debian** machine. Nothing here needs
internet access to *solve* — only to install the tools the first time.

## Quick setup

```bash
# 1. install everything (Kali/Ubuntu/Debian)
bash setup/install-kali.sh

# 2. confirm your machine is ready
bash setup/check-tools.sh

# 3. launch the lab
python3 Cryptography.py
```

## What gets installed

| Package | Provides | Used by |
|---------|----------|---------|
| `python3` | the lab portal + solver scripts | portal, 3, 4, 7, 10 |
| `openssl` | encryption/cert/TLS toolkit | 2, 5, 8, 9, 11 |
| `coreutils` | `base64`, `sha256sum`, `sha1sum` | 7, 11 |
| `xxd` | hex dump/undump | 3, 5 (handy) |
| `hashid` | identify a hash type | 6, 11 |
| `hashcat` and/or `john` | crack a hash against a wordlist | 6, 11 |

On **Kali**, most of these are pre-installed — `check-tools.sh` will tell you if
anything is missing.

## About hashcat vs John

Either tool solves the cracking challenges (6 and 11). If `hashcat` complains that
it can't find an OpenCL device (common inside a VM), you can:

- add `--force` to run on CPU, or
- just use **John the Ripper** instead — it's CPU-based and needs no GPU:
  ```bash
  john --format=raw-sha1 --wordlist=wordlist.txt hash.txt      # challenge 6
  john --format=raw-md5  --wordlist=wordlist.txt s2.hash       # challenge 11
  ```

The provided wordlists are tiny, so both tools finish instantly.

## CyberChef (optional, offline)

Several challenges (1, 3, 4, 11) can be solved in **CyberChef** if you prefer a GUI
to the command line. CyberChef runs entirely in your browser with no internet:

1. Download the standalone build from the official GitHub releases page
   (`gchq/CyberChef`) — a single `CyberChef_vX.html` file — on a machine that *does*
   have internet, then copy it into your lab VM.
2. Double-click that HTML file to open it in your browser. That's it — it works fully
   offline.

Useful CyberChef operations for this lab: *ROT13 Brute Force*, *XOR*, *XOR Brute
Force*, *From Base64*, *From Hex*, *RSA* helpers, and the various *Hash* operations.

CyberChef is **optional** — every challenge is fully solvable with the command-line
tools above.
