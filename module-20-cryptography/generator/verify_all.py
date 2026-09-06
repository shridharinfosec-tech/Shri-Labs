#!/usr/bin/env python3
"""
SIS Module 20 Cryptography labs - automated solver / verifier.
Solves every lab the way a trainee would (python + openssl) and checks the
recovered flag against the shipped manifest hash. Run after every re-roll:

    python3 generator/verify_all.py

Exit 0 = all solvable, 1 = something is broken. (The MD5/SHA-1 crack labs are
solved here by simulating the hashcat/john dictionary attack in Python, proving
the password is crackable from the provided wordlist.)
"""
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "challenges"
LAB = ROOT / ".lab"
OSSL = shutil.which("openssl")
MANI = json.load(open(LAB / "manifest.json"))
SALT = bytes.fromhex(MANI["salt"])
ITERS = MANI.get("pbkdf2_iters", 100_000)
BY_ID = {c["id"]: c for c in MANI["challenges"]}


def ossl(*a, inp=None):
    return subprocess.run([OSSL, *a], input=inp, capture_output=True)


def fh(flag):
    return hashlib.pbkdf2_hmac("sha256", flag.encode(), SALT, ITERS).hex()


def find_flag(t):
    m = re.search(r"SIS\{[^}]*\}", t)
    return m.group(0) if m else None


def s01():
    b = open(CH / "01-base64" / "token.txt").read().strip()
    return find_flag(base64.b64decode(base64.b64decode(b)).decode(errors="replace"))


def s02():
    h = open(CH / "02-hex" / "value.hex").read().strip()
    return find_flag(bytes.fromhex(h).decode(errors="replace"))


def s03():
    bits = open(CH / "03-binary" / "bits.txt").read().split()
    return find_flag(bytes(int(b, 2) for b in bits).decode(errors="replace"))


def s04():
    s = open(CH / "04-caesar" / "ciphertext.txt").read()
    for k in range(1, 26):
        d = "".join(chr((ord(c) - 65 - k) % 26 + 65) if c.isupper()
                    else chr((ord(c) - 97 - k) % 26 + 97) if c.islower() else c for c in s)
        f = find_flag(d)
        if f:
            return f


def s05():
    s = open(CH / "05-atbash" / "ciphertext.txt").read()
    d = "".join(chr(219 - ord(c)) if "a" <= c <= "z" else chr(155 - ord(c)) if "A" <= c <= "Z" else c for c in s)
    return find_flag(d)


def s06():
    d = CH / "06-vigenere"
    key = [k for k in re.search(r"keyword:\s*(\w+)", open(d / "key.txt").read(), re.I).group(1).lower() if k.isalpha()]
    ct = open(d / "ciphertext.txt").read()
    out, ki = [], 0
    for c in ct:
        if c.isalpha():
            k = ord(key[ki % len(key)]) - 97
            base = 65 if c.isupper() else 97
            out.append(chr((ord(c) - base - k) % 26 + base)); ki += 1
        else:
            out.append(c)
    return find_flag("".join(out))


def s07():
    d = CH / "07-aes-decrypt"
    t = open(d / "key.txt").read()
    K = re.search(r"Key \(hex\):\s*([0-9a-fA-F]{64})", t).group(1)
    IV = re.search(r"IV\s*\(hex\):\s*([0-9a-fA-F]{32})", t).group(1)
    out = ossl("enc", "-d", "-aes-256-cbc", "-in", str(d / "secret.enc"), "-K", K, "-iv", IV)
    return find_flag(out.stdout.decode(errors="replace"))


def s08():
    d = CH / "08-rsa-decrypt"
    out = ossl("pkeyutl", "-decrypt", "-inkey", str(d / "private.pem"), "-in", str(d / "message.enc"))
    return find_flag(out.stdout.decode(errors="replace"))


def s09():
    d = CH / "09-hybrid"
    sk = ossl("pkeyutl", "-decrypt", "-inkey", str(d / "private.pem"),
              "-in", str(d / "session_key.enc")).stdout.decode().strip()
    iv = re.search(r"[0-9a-fA-F]{32}", open(d / "iv.txt").read()).group(0)
    out = ossl("enc", "-d", "-aes-256-cbc", "-in", str(d / "data.enc"), "-K", sk, "-iv", iv)
    return find_flag(out.stdout.decode(errors="replace"))


def _crack(slug, algo):
    d = CH / slug
    h = open(d / "hash.txt").read().strip()
    fn = hashlib.md5 if algo == "md5" else hashlib.sha1
    for w in open(d / "wordlist.txt").read().splitlines():
        if fn(w.encode()).hexdigest() == h:
            return f"SIS{{{w}}}"


def s10():
    return _crack("10-md5-crack", "md5")


def s11():
    return _crack("11-sha1-crack", "sha1")


def s12():
    d = CH / "12-integrity"
    ht = hashlib.sha256(open(d / "tampered.txt", "rb").read()).hexdigest()
    out = subprocess.run([sys.executable, "unlock.py", ht], cwd=str(d), capture_output=True)
    return find_flag(out.stdout.decode(errors="replace"))


SOLVERS = [("01", s01), ("02", s02), ("03", s03), ("04", s04), ("05", s05), ("06", s06),
           ("07", s07), ("08", s08), ("09", s09), ("10", s10), ("11", s11), ("12", s12)]


def main():
    if not OSSL:
        sys.exit("openssl not found on PATH")
    print(f"Verifying batch '{MANI['batch']}' ({len(SOLVERS)} labs)\n")
    ok = True
    for cid, fn in SOLVERS:
        title = BY_ID[cid]["title"]
        try:
            flag = fn()
            passed = flag is not None and fh(flag) == BY_ID[cid]["flag_pbkdf2"]
        except Exception as e:
            flag, passed = f"ERROR: {e}", False
        print(f"  [{'PASS' if passed else 'FAIL'}] {cid:<3} {title[:32]:<32} {flag}")
        ok = ok and passed
    print()
    if ok:
        print("ALL LABS SOLVABLE - flags match the manifest.")
        sys.exit(0)
    print("SOME LABS FAILED - fix before shipping.")
    sys.exit(1)


if __name__ == "__main__":
    main()
