#!/usr/bin/env python3
"""
SIS CEH v13 - Module 20 Cryptography - Lab Generator
====================================================
Builds 12 beginner (easy) hands-on labs across four topic tracks:

  Encoding & Decoding   -  Base64, Hex, Binary
  Classical Ciphers     -  Caesar, Atbash, Vigenere
  Encryption & Decryption - AES-256-CBC, RSA (private key), Hybrid RSA+AES
  Hashing & Integrity   -  MD5 crack, SHA-1 crack, SHA-256 integrity

Every lab produces REAL artefacts (encoded files, keys, hashes) and a fresh,
per-batch random flag, so no two training batches share answers.

Dependencies: python3 standard library + the `openssl` CLI (both pre-installed
              on Kali / Ubuntu).

Usage:
    python3 generate_all.py                 # fresh random batch
    python3 generate_all.py --seed 1234     # reproducible batch
    python3 generate_all.py --batch AUG2025 # label the batch
"""

import argparse
import base64
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CH = ROOT / "challenges"
LAB = ROOT / ".lab"
OSSL = shutil.which("openssl")
if OSSL is None:
    sys.exit("ERROR: openssl not found on PATH. Install openssl and try again.")

PBKDF2_ITERS = 100_000


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def ossl(*args, inp=None):
    return subprocess.run([OSSL, *args], input=inp, capture_output=True, check=True)


def egcd(a, b):
    if b == 0:
        return (a, 1, 0)
    g, x, y = egcd(b, a % b)
    return (g, y, x - (a // b) * y)


def modinv(a, m):
    g, x, _ = egcd(a % m, m)
    if g != 1:
        raise ValueError("no modular inverse")
    return x % m


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def keystream(km: bytes, n: int) -> bytes:
    out, i = b"", 0
    while len(out) < n:
        out += hashlib.sha256(km + i.to_bytes(4, "big")).digest()
        i += 1
    return out[:n]


def sha_lock(plaintext: bytes, km: bytes) -> str:
    return xor(plaintext, keystream(km, len(plaintext))).hex()


def write_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def write_text(path: Path, text: str):
    write_bytes(path, text.replace("\r\n", "\n").encode())


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def flag_hash(flag: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", flag.encode(), bytes.fromhex(salt_hex),
                               PBKDF2_ITERS).hex()


class Flags:
    def __init__(self, rng):
        self.rng = rng

    def suffix(self, n=4):
        return "".join(self.rng.choice("0123456789abcdef") for _ in range(n))

    def make(self, phrase):
        return f"SIS{{{phrase}-{self.suffix()}}}"


# ---- classical cipher primitives ----
def caesar(text, shift):
    out = []
    for c in text:
        if c.isupper():
            out.append(chr((ord(c) - 65 + shift) % 26 + 65))
        elif c.islower():
            out.append(chr((ord(c) - 97 + shift) % 26 + 97))
        else:
            out.append(c)
    return "".join(out)


def atbash(text):
    out = []
    for c in text:
        if "a" <= c <= "z":
            out.append(chr(219 - ord(c)))   # a<->z  (97+122)
        elif "A" <= c <= "Z":
            out.append(chr(155 - ord(c)))   # A<->Z  (65+90)
        else:
            out.append(c)
    return "".join(out)


def vigenere_encrypt(text, key):
    out, ki = [], 0
    key = [k for k in key.lower() if k.isalpha()]
    for c in text:
        if c.isalpha():
            k = ord(key[ki % len(key)]) - 97
            base = 65 if c.isupper() else 97
            out.append(chr((ord(c) - base + k) % 26 + base))
            ki += 1
        else:
            out.append(c)
    return "".join(out)


# ---- wordlist for the crack labs ----
BASE_WORDS = [
    "sunshine", "dragon", "monsoon", "shadowfax", "falcon", "matrix", "phoenix",
    "titanium", "avalanche", "keystone", "nightfall", "riverdale", "thunder",
    "kryptonite", "sapphire", "obsidian", "wildfire", "moonlight", "cobalt",
    "voyager", "meridian", "cascade", "granite", "everest", "himalaya",
    "password", "welcome", "letmein", "qwerty", "iloveyou", "trustno1",
    "hunter", "superman", "batman", "football", "mumbai", "chennai",
    "kolkata", "bangalore", "hyderabad", "ganges", "deccan", "konkan",
    "nilgiri", "vindhya", "aravalli", "chinar", "monsoon", "tempest",
]


def build_wordlist(rng, targets, size=600):
    words = set()
    while len(words) < size:
        base = rng.choice(BASE_WORDS)
        style = rng.randint(0, 4)
        if style == 0:
            w = base
        elif style == 1:
            w = base + str(rng.randint(1, 9999))
        elif style == 2:
            w = base.capitalize() + str(rng.randint(10, 99))
        elif style == 3:
            w = base + rng.choice(["!", "@", "#", "123", "007"])
        else:
            w = base.replace("o", "0").replace("i", "1")
        words.add(w)
    for t in targets:
        words.discard(t)
    words = list(words)
    rng.shuffle(words)
    for t in targets:
        words.insert(rng.randint(0, len(words)), t)
    return words


# ==========================================================================
# CHALLENGE GENERATORS  (each returns {flag, files, solution})
# ==========================================================================

# ---- Encoding & Decoding ----
def gen_base64(rng, flags):
    d = CH / "01-base64"
    flag = flags.make("base64-is-just-encoding")
    msg = ("Base64 only re-packages bytes into printable characters - it has no key, "
           "so anyone can reverse it. Flag: " + flag)
    once = base64.b64encode(msg.encode())
    twice = base64.b64encode(once)                     # double-encoded
    write_text(d / "token.txt", twice.decode() + "\n")
    write_text(d / "hint.txt",
               "This is Base64, not encryption. Decode it... then notice the result is\n"
               "STILL Base64, so decode again.  CyberChef: 'From Base64' (x2), or the terminal.\n")
    dec = base64.b64decode(base64.b64decode(open(d / "token.txt").read().strip()))
    assert flag in dec.decode(), "base64 self-check"
    sol = "```bash\nbase64 -d token.txt | base64 -d\n```\n"
    return {"flag": flag, "files": ["token.txt"], "solution": sol}


def gen_hex(rng, flags):
    d = CH / "02-hex"
    flag = flags.make("hex-is-not-a-secret")
    msg = ("Hex just writes each byte as two characters 0-9 a-f. It is an encoding, "
           "not a cipher. Flag: " + flag)
    write_text(d / "value.hex", msg.encode().hex() + "\n")
    write_text(d / "hint.txt",
               "This is hexadecimal (0-9, a-f). Convert it back to text.\n"
               "CyberChef: 'From Hex'.  Terminal: pipe it through xxd -r -p.\n")
    dec = bytes.fromhex(open(d / "value.hex").read().strip())
    assert flag in dec.decode(), "hex self-check"
    sol = "```bash\nxxd -r -p value.hex\n# or:  cat value.hex | xxd -r -p\n```\n"
    return {"flag": flag, "files": ["value.hex"], "solution": sol}


def gen_binary(rng, flags):
    d = CH / "03-binary"
    flag = flags.make("binary-decodes-to-ascii")
    msg = "Each group below is one byte in binary (8 bits). Decode to ASCII. Flag: " + flag
    enc = " ".join(format(b, "08b") for b in msg.encode())
    write_text(d / "bits.txt", enc + "\n")
    write_text(d / "hint.txt",
               "Every 8-bit group is one ASCII character. Convert binary -> text.\n"
               "CyberChef: 'From Binary'.  Or a couple of lines of Python.\n")
    dec = bytes(int(b, 2) for b in open(d / "bits.txt").read().split())
    assert flag in dec.decode(), "binary self-check"
    sol = ("```bash\npython3 -c \"print(''.join(chr(int(b,2)) for b in "
           "open('bits.txt').read().split()))\"\n```\n")
    return {"flag": flag, "files": ["bits.txt"], "solution": sol}


# ---- Classical Ciphers ----
def gen_caesar(rng, flags):
    d = CH / "04-caesar"
    flag = flags.make("caesar-shift-is-not-security")
    shift = rng.randint(3, 23)
    msg = ("A Caesar cipher shifts every letter by a fixed amount, and there are only 25 "
           "possible shifts, so trying them all breaks it instantly. Flag: " + flag)
    write_text(d / "ciphertext.txt", caesar(msg, shift) + "\n")
    write_text(d / "hint.txt",
               "A Caesar cipher has only 25 keys - try every shift.\n"
               "CyberChef: 'ROT13 Brute Force'.  Or brute-force in one line of Python.\n")
    sol = (f"Shift = {shift}.\n\n```bash\n"
           "python3 - <<'EOF'\n"
           "s=open('ciphertext.txt').read()\n"
           "for k in range(1,26):\n"
           "    print(k, ''.join(chr((ord(c)-65-k)%26+65) if c.isupper() else "
           "chr((ord(c)-97-k)%26+97) if c.islower() else c for c in s))\n"
           "EOF\n```\n")
    return {"flag": flag, "files": ["ciphertext.txt"], "solution": sol}


def gen_atbash(rng, flags):
    d = CH / "05-atbash"
    flag = flags.make("atbash-mirrors-the-alphabet")
    msg = ("Atbash swaps each letter with its mirror in the alphabet (A<->Z, B<->Y). "
           "Applying it a second time undoes it. Flag: " + flag)
    write_text(d / "ciphertext.txt", atbash(msg) + "\n")
    write_text(d / "hint.txt",
               "This is the Atbash cipher: the alphabet reversed (A<->Z, B<->Y ...).\n"
               "Atbash is its own inverse - apply it again to decode.\n"
               "CyberChef: 'Atbash Cipher'.\n")
    assert flag in atbash(open(d / "ciphertext.txt").read().strip()), "atbash self-check"
    sol = ("```bash\npython3 -c \"import sys;print(''.join(chr(219-ord(c)) if 'a'<=c<='z' "
           "else chr(155-ord(c)) if 'A'<=c<='Z' else c for c in open('ciphertext.txt').read()))\"\n```\n")
    return {"flag": flag, "files": ["ciphertext.txt"], "solution": sol}


def gen_vigenere(rng, flags):
    d = CH / "06-vigenere"
    flag = flags.make("vigenere-needs-the-keyword")
    key = rng.choice(["shield", "cipher", "vault", "secure", "matrix", "falcon"])
    msg = ("The Vigenere cipher shifts each letter by a different amount driven by a repeating "
           "keyword. With the keyword in hand, decryption is easy. Flag: " + flag)
    write_text(d / "ciphertext.txt", vigenere_encrypt(msg, key) + "\n")
    write_text(d / "key.txt", f"Vigenere keyword: {key}\n")
    write_text(d / "hint.txt",
               "This is a Vigenere cipher and you have the keyword (key.txt).\n"
               "CyberChef: 'Vigenere Decode' and paste the key.  Or decrypt in Python.\n")
    sol = (f"Keyword = `{key}`.\n\n```bash\n"
           "python3 - <<'EOF'\n"
           f"key='{key}'; ct=open('ciphertext.txt').read(); out=[]; ki=0\n"
           "for c in ct:\n"
           "    if c.isalpha():\n"
           "        k=ord(key[ki%len(key)].lower())-97; b=65 if c.isupper() else 97\n"
           "        out.append(chr((ord(c)-b-k)%26+b)); ki+=1\n"
           "    else: out.append(c)\n"
           "print(''.join(out))\n"
           "EOF\n```\n")
    return {"flag": flag, "files": ["ciphertext.txt", "key.txt"], "solution": sol}


# ---- Encryption & Decryption ----
def gen_aes(rng, flags):
    d = CH / "07-aes-decrypt"
    flag = flags.make("aes-256-cbc-with-the-right-key")
    key = bytes(rng.randint(0, 255) for _ in range(32)).hex()
    iv = bytes(rng.randint(0, 255) for _ in range(16)).hex()
    plain = ("SIS Secure Bank - recovered backup file\n"
             "Encrypted with AES-256 in CBC mode.\n\n"
             f"FLAG: {flag}\n")
    tmp = Path(tempfile.mkdtemp())
    pt = tmp / "p.txt"
    write_bytes(pt, plain.encode())
    ossl("enc", "-aes-256-cbc", "-in", str(pt), "-out", str(d / "secret.enc"),
         "-K", key, "-iv", iv)
    write_text(d / "key.txt", f"Key (hex): {key}\nIV  (hex): {iv}\n")
    write_text(d / "hint.txt",
               "AES-256 in CBC mode. You have the key and IV (key.txt).\n"
               "openssl enc -d -aes-256-cbc  with  -K (key)  -iv (iv)  -in  -out\n")
    dec = ossl("enc", "-d", "-aes-256-cbc", "-in", str(d / "secret.enc"),
               "-K", key, "-iv", iv).stdout.decode()
    assert flag in dec, "aes self-check"
    shutil.rmtree(tmp, ignore_errors=True)
    sol = (f"```bash\nopenssl enc -d -aes-256-cbc -in secret.enc -out secret.txt \\\n"
           f"  -K {key} \\\n  -iv {iv}\ncat secret.txt\n```\n")
    return {"flag": flag, "files": ["secret.enc", "key.txt"], "solution": sol}


def gen_rsa(rng, flags):
    d = CH / "08-rsa-decrypt"
    flag = flags.make("rsa-decrypts-with-the-private-key")
    tmp = Path(tempfile.mkdtemp())
    priv, pub = tmp / "private.pem", tmp / "public.pem"
    ossl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(priv))
    ossl("pkey", "-in", str(priv), "-pubout", "-out", str(pub))
    msg = tmp / "m.txt"
    write_bytes(msg, (f"RSA only reverses with the matching private key.\nFLAG: {flag}\n").encode())
    ossl("pkeyutl", "-encrypt", "-pubin", "-inkey", str(pub),
         "-in", str(msg), "-out", str(d / "message.enc"))
    shutil.copy(priv, d / "private.pem")
    write_text(d / "hint.txt",
               "message.enc was encrypted with an RSA public key. You hold the matching\n"
               "PRIVATE key (private.pem) - use it to decrypt.\n"
               "openssl pkeyutl -decrypt -inkey private.pem -in message.enc\n")
    dec = ossl("pkeyutl", "-decrypt", "-inkey", str(d / "private.pem"),
               "-in", str(d / "message.enc")).stdout.decode()
    assert flag in dec, "rsa self-check"
    shutil.rmtree(tmp, ignore_errors=True)
    sol = ("```bash\nopenssl pkeyutl -decrypt -inkey private.pem -in message.enc\n```\n")
    return {"flag": flag, "files": ["private.pem", "message.enc"], "solution": sol}


def gen_hybrid(rng, flags):
    d = CH / "09-hybrid"
    flag = flags.make("hybrid-rsa-wraps-the-aes-key")
    tmp = Path(tempfile.mkdtemp())
    priv, pub = tmp / "private.pem", tmp / "public.pem"
    ossl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(priv))
    ossl("pkey", "-in", str(priv), "-pubout", "-out", str(pub))
    aes_key = bytes(rng.randint(0, 255) for _ in range(32)).hex()
    iv = bytes(rng.randint(0, 255) for _ in range(16)).hex()
    skf = tmp / "sk.txt"
    write_bytes(skf, aes_key.encode())
    ossl("pkeyutl", "-encrypt", "-pubin", "-inkey", str(pub),
         "-in", str(skf), "-out", str(d / "session_key.enc"))
    blob = tmp / "blob.txt"
    write_bytes(blob, (f"Hybrid encryption: RSA wrapped the AES key, AES protects this data.\n"
                       f"FLAG: {flag}\n").encode())
    ossl("enc", "-aes-256-cbc", "-in", str(blob), "-out", str(d / "data.enc"),
         "-K", aes_key, "-iv", iv)
    shutil.copy(priv, d / "private.pem")
    write_text(d / "iv.txt", f"AES IV (hex): {iv}\n")
    write_text(d / "hint.txt",
               "Hybrid encryption (the TLS pattern):\n"
               " - session_key.enc = an AES key encrypted with RSA.\n"
               " - data.enc        = the data, encrypted with AES-256-CBC using that key.\n"
               "1) RSA-decrypt session_key.enc with private.pem -> a 64-hex AES key.\n"
               "2) AES-decrypt data.enc with that key (-K) and the IV in iv.txt.\n")
    rk = ossl("pkeyutl", "-decrypt", "-inkey", str(d / "private.pem"),
              "-in", str(d / "session_key.enc")).stdout.decode()
    dec = ossl("enc", "-d", "-aes-256-cbc", "-in", str(d / "data.enc"),
               "-K", rk, "-iv", iv).stdout.decode()
    assert flag in dec, "hybrid self-check"
    shutil.rmtree(tmp, ignore_errors=True)
    sol = ("```bash\n"
           "openssl pkeyutl -decrypt -inkey private.pem -in session_key.enc -out sk.txt\n"
           f"openssl enc -d -aes-256-cbc -in data.enc -K $(cat sk.txt) -iv {iv}\n```\n")
    return {"flag": flag,
            "files": ["private.pem", "session_key.enc", "data.enc", "iv.txt"],
            "solution": sol}


# ---- Hashing & Integrity ----
def _crack_lab(d, algo, password, hcat_mode, john_fmt):
    if algo == "md5":
        h = hashlib.md5(password.encode()).hexdigest()
    else:
        h = hashlib.sha1(password.encode()).hexdigest()
    write_text(d / "hash.txt", h + "\n")
    write_text(d / "hint.txt",
               f"Identify the hash, then crack it against wordlist.txt.\n"
               f"  hashid hash.txt\n"
               f"  hashcat -m {hcat_mode} -a 0 hash.txt wordlist.txt --show\n"
               f"  john --format={john_fmt} --wordlist=wordlist.txt hash.txt\n"
               f"The cracked word goes inside the flag braces: SIS{{crackedword}}\n")
    sol = (f"Hash = {algo.upper()}, password = `{password}`.\n\n```bash\n"
           f"hashid hash.txt\n"
           f"hashcat -m {hcat_mode} -a 0 hash.txt wordlist.txt --show\n"
           f"john --format={john_fmt} --wordlist=wordlist.txt hash.txt\n```\n"
           f"Flag = `SIS{{{password}}}`.\n")
    return sol


def gen_md5_crack(rng, flags, password):
    d = CH / "10-md5-crack"
    flag = f"SIS{{{password}}}"
    sol = _crack_lab(d, "md5", password, 0, "raw-md5")
    return {"flag": flag, "files": ["hash.txt", "wordlist.txt"], "solution": sol}


def gen_sha1_crack(rng, flags, password):
    d = CH / "11-sha1-crack"
    flag = f"SIS{{{password}}}"
    sol = _crack_lab(d, "sha1", password, 100, "raw-sha1")
    return {"flag": flag, "files": ["hash.txt", "wordlist.txt"], "solution": sol}


def gen_integrity(rng, flags):
    d = CH / "12-integrity"
    flag = flags.make("sha256-detects-a-single-byte-change")
    acct = rng.randint(10**9, 10**10 - 1)
    orig_amt = 50000
    tamp_amt = rng.choice([95000, 500000, 45000, 5000000])
    original = (f"SIS Secure Bank - Wire Transfer Instruction\n"
                f"Beneficiary: Shridhar Infosec Solutions\n"
                f"Account No : {acct}\n"
                f"Amount     : Rs {orig_amt}\n"
                f"Reference  : CEH v13 training invoice\n"
                f"Authorised : yes\n")
    tampered = original.replace(f"Rs {orig_amt}", f"Rs {tamp_amt}")
    write_text(d / "original.txt", original)
    write_text(d / "tampered.txt", tampered)
    h_tamp = sha256_hex(tampered.replace("\r\n", "\n").encode())
    write_text(d / "flag.enc", sha_lock(flag.encode(), h_tamp.encode()) + "\n")
    write_text(d / "unlock.py", UNLOCK_PY)
    write_text(d / "hint.txt",
               "One of the two files was tampered with. They look almost identical.\n"
               "1) sha256sum original.txt tampered.txt  (the hashes differ)\n"
               "2) diff them to see what changed (report it).\n"
               "3) Prove you computed it: python3 unlock.py <sha256-of-tampered.txt>\n")
    locked = bytes.fromhex((d / "flag.enc").read_text().strip())
    assert xor(locked, keystream(h_tamp.encode(), len(locked))).decode() == flag
    sol = (f"Changed field: Amount `Rs {orig_amt}` -> `Rs {tamp_amt}`.\n"
           f"SHA-256 of tampered.txt: `{h_tamp}`\n\n```bash\n"
           "sha256sum original.txt tampered.txt\n"
           f"python3 unlock.py {h_tamp}\n```\n")
    return {"flag": flag,
            "files": ["original.txt", "tampered.txt", "flag.enc", "unlock.py"],
            "solution": sol}


UNLOCK_PY = '''#!/usr/bin/env python3
"""Feed this the SHA-256 of tampered.txt to reveal the flag.
Usage:  python3 unlock.py <sha256-hex-of-tampered.txt>
        (get it from:  sha256sum tampered.txt)
"""
import sys, hashlib

def keystream(km, n):
    out=b""; c=0
    while len(out)<n:
        out+=hashlib.sha256(km+c.to_bytes(4,"big")).digest(); c+=1
    return out[:n]

if len(sys.argv)!=2:
    print(__doc__); sys.exit(1)
digest="".join(ch for ch in sys.argv[1].strip().lower() if ch in "0123456789abcdef")
if len(digest)!=64:
    print("That is not a SHA-256 hash (need 64 hex chars)."); sys.exit(1)
ct=bytes.fromhex(open("flag.enc").read().strip())
pt=bytes(a^b for a,b in zip(ct,keystream(digest.encode(),len(ct))))
try:
    text=pt.decode()
except UnicodeDecodeError:
    text=""
print("Correct! Flag: "+text if text.startswith("SIS{") else
      "Wrong hash. Run sha256sum on tampered.txt (the exact file) and try again.")
'''


# ==========================================================================
# Topic categories + EC-Council style lab manuals (scenario + detailed steps)
# ==========================================================================
CATEGORY_ORDER = [
    "Encoding & Decoding",
    "Classical Ciphers",
    "Encryption & Decryption",
    "Hashing & Integrity",
]
CATEGORIES = {
    "01": "Encoding & Decoding", "02": "Encoding & Decoding", "03": "Encoding & Decoding",
    "04": "Classical Ciphers", "05": "Classical Ciphers", "06": "Classical Ciphers",
    "07": "Encryption & Decryption", "08": "Encryption & Decryption", "09": "Encryption & Decryption",
    "10": "Hashing & Integrity", "11": "Hashing & Integrity", "12": "Hashing & Integrity",
}

GUIDES = {
 "01": {"time": "~5 min",
  "scenario": ("During a web-application assessment you intercept an API request whose body is an "
    "opaque-looking string. It is not encrypted - it is Base64-encoded, and in fact encoded twice. "
    "Because Base64 has no key, you can simply decode it and read the data it carries."),
  "objective": "Decode the Base64 token (it is double-encoded) and read the flag inside.",
  "steps": [
    {"title": "Inspect the token", "desc": "It uses only A-Z a-z 0-9 + / with '=' padding - the classic Base64 alphabet.",
     "cmd": "cat token.txt"},
    {"title": "Decode the first Base64 layer", "desc": "The output will still look like Base64 - that is expected, it was encoded twice.",
     "cmd": "base64 -d token.txt"},
    {"title": "Decode the second layer", "desc": "Pipe the first decode into base64 again to reach the plaintext and the SIS{...} flag.",
     "cmd": "base64 -d token.txt | base64 -d"},
    {"title": "CyberChef alternative", "desc": "Drop the token in and chain 'From Base64' twice, or use the 'Magic' operation to auto-detect.", "cmd": ""},
  ]},
 "02": {"time": "~5 min",
  "scenario": ("A configuration file stores a value as a long hexadecimal string. Hex is an encoding "
    "(each byte written as two characters 0-9 a-f), not a cipher, so it converts straight back to "
    "readable text."),
  "objective": "Convert the hex string back to ASCII and read the flag.",
  "steps": [
    {"title": "Look at the value", "desc": "Only characters 0-9 and a-f, an even number of them - that is hexadecimal.",
     "cmd": "cat value.hex"},
    {"title": "Convert hex to text", "desc": "xxd -r -p reverses a plain hex dump back to raw bytes.",
     "cmd": "xxd -r -p value.hex"},
    {"title": "CyberChef alternative", "desc": "Use the 'From Hex' operation to get the same result in the browser.", "cmd": ""},
  ]},
 "03": {"time": "~5 min",
  "scenario": ("A device log records one of its fields as a raw bit-stream. Each group of eight bits "
    "is one ASCII character, so the stream converts directly back to text."),
  "objective": "Convert the 8-bit binary groups back to ASCII and read the flag.",
  "steps": [
    {"title": "Inspect the stream", "desc": "Space-separated groups of eight 1s and 0s - one byte each.",
     "cmd": "cat bits.txt"},
    {"title": "Convert binary to text", "desc": "Turn every 8-bit group into its character.",
     "cmd": "python3 -c \"print(''.join(chr(int(b,2)) for b in open('bits.txt').read().split()))\""},
    {"title": "CyberChef alternative", "desc": "Use 'From Binary' (delimiter: Space) to decode it in the browser.", "cmd": ""},
  ]},
 "04": {"time": "~5 min",
  "scenario": ("An old in-house application 'protects' a note with a Caesar cipher - every letter shifted "
    "by a fixed amount. With only 25 possible shifts, brute force recovers the note in seconds. This is "
    "why classical ciphers were abandoned for real algorithms."),
  "objective": "Brute-force the Caesar shift and read the flag inside the recovered message.",
  "steps": [
    {"title": "Read the ciphertext", "desc": "Readable letters, just shifted by an unknown fixed amount.",
     "cmd": "cat ciphertext.txt"},
    {"title": "Try all 25 shifts", "desc": "One of the 25 lines will turn into plain English ending in a SIS{...} flag.",
     "cmd": "python3 - <<'EOF'\ns=open('ciphertext.txt').read()\nfor k in range(1,26):\n    print(k, ''.join(chr((ord(c)-65-k)%26+65) if c.isupper() else chr((ord(c)-97-k)%26+97) if c.islower() else c for c in s))\nEOF"},
    {"title": "CyberChef alternative", "desc": "Use 'ROT13 Brute Force' and read the line that becomes English.", "cmd": ""},
  ]},
 "05": {"time": "~5 min",
  "scenario": ("A message was obfuscated with the Atbash cipher, which replaces each letter with its "
    "mirror in the alphabet (A becomes Z, B becomes Y). Atbash is its own inverse, so applying it a "
    "second time reveals the text."),
  "objective": "Undo the Atbash substitution and read the flag.",
  "steps": [
    {"title": "Read the ciphertext", "desc": "A monoalphabetic substitution - each letter mapped to its alphabet mirror.",
     "cmd": "cat ciphertext.txt"},
    {"title": "Apply Atbash again to decode", "desc": "Mirroring the alphabet a second time restores the original text.",
     "cmd": "python3 -c \"print(''.join(chr(219-ord(c)) if 'a'<=c<='z' else chr(155-ord(c)) if 'A'<=c<='Z' else c for c in open('ciphertext.txt').read()))\""},
    {"title": "CyberChef alternative", "desc": "Use the 'Atbash Cipher' operation.", "cmd": ""},
  ]},
 "06": {"time": "~7 min",
  "scenario": ("A message was encrypted with the Vigenere cipher, which shifts each letter by a varying "
    "amount driven by a repeating keyword. During the assessment you already recovered the keyword, so "
    "decryption is straightforward."),
  "objective": "Use the recovered keyword to decrypt the Vigenere ciphertext and read the flag.",
  "steps": [
    {"title": "Read the ciphertext and keyword", "desc": "The keyword is in key.txt.",
     "cmd": "cat ciphertext.txt key.txt"},
    {"title": "Decrypt with the keyword", "desc": "Subtract the keyword's letter shifts to recover the plaintext.",
     "cmd": "python3 - <<'EOF'\nkey='KEYWORD'   # <- put the keyword from key.txt here (lowercase)\nct=open('ciphertext.txt').read(); out=[]; ki=0\nfor c in ct:\n    if c.isalpha():\n        k=ord(key[ki%len(key)].lower())-97; b=65 if c.isupper() else 97\n        out.append(chr((ord(c)-b-k)%26+b)); ki+=1\n    else: out.append(c)\nprint(''.join(out))\nEOF"},
    {"title": "CyberChef alternative", "desc": "Use 'Vigenere Decode' and paste the keyword from key.txt.", "cmd": ""},
  ]},
 "07": {"time": "~7 min",
  "scenario": ("You recovered an AES-256-CBC encrypted file from a misconfigured backup, along with the "
    "key and initialisation vector that were stored next to it. With the key material in hand, OpenSSL "
    "decrypts it directly."),
  "objective": "Decrypt secret.enc with the supplied key and IV, then read the flag.",
  "steps": [
    {"title": "Read the key and IV", "desc": "key.txt holds a 64-hex-char AES-256 key and a 32-hex-char IV.",
     "cmd": "cat key.txt"},
    {"title": "Decrypt with OpenSSL", "desc": "Pass the key to -K and the IV to -iv (both hex). Replace the placeholders with the real values.",
     "cmd": "openssl enc -d -aes-256-cbc -in secret.enc -out secret.txt -K <key-hex> -iv <iv-hex>"},
    {"title": "Read the flag", "desc": "The decrypted file contains the SIS{...} flag.",
     "cmd": "cat secret.txt"},
  ]},
 "08": {"time": "~7 min",
  "scenario": ("You obtained an RSA private key and a small file that was encrypted for the matching "
    "public key. Whatever the public key locked, only this private key can open - so the file decrypts "
    "cleanly."),
  "objective": "Use the RSA private key to decrypt message.enc and read the flag.",
  "steps": [
    {"title": "Confirm what you have", "desc": "private.pem is the RSA private key; message.enc is the ciphertext.",
     "cmd": "openssl pkey -in private.pem -noout -text | head -3"},
    {"title": "Decrypt with the private key", "desc": "pkeyutl -decrypt reverses the public-key encryption.",
     "cmd": "openssl pkeyutl -decrypt -inkey private.pem -in message.enc"},
    {"title": "Read the flag", "desc": "The recovered plaintext carries the SIS{...} flag.", "cmd": ""},
  ]},
 "09": {"time": "~10 min",
  "scenario": ("A captured payload uses hybrid encryption - exactly how TLS works. A random AES session "
    "key was wrapped with RSA, and the bulk data was encrypted with that AES key. You hold the RSA "
    "private key, so you can unwrap the session key and then decrypt the data."),
  "objective": "RSA-decrypt the AES session key, then AES-decrypt the data blob to read the flag.",
  "steps": [
    {"title": "Recover the AES session key with RSA", "desc": "The result is a 64-hex-character AES key.",
     "cmd": "openssl pkeyutl -decrypt -inkey private.pem -in session_key.enc -out sk.txt\ncat sk.txt"},
    {"title": "Read the IV", "desc": "iv.txt holds the AES initialisation vector.",
     "cmd": "cat iv.txt"},
    {"title": "Decrypt the data with AES", "desc": "Feed the recovered key to -K and the IV to -iv.",
     "cmd": "openssl enc -d -aes-256-cbc -in data.enc -K $(cat sk.txt) -iv <iv-hex>"},
  ]},
 "10": {"time": "~10 min",
  "scenario": ("You extracted a password hash from a leaked database dump during an authorised assessment. "
    "Hashes cannot be reversed, but weak passwords fall to a dictionary attack: hash every word in a list "
    "and compare. Identify the algorithm first, then crack it."),
  "objective": "Identify the hash type, crack it against the wordlist; the cracked password is the flag.",
  "steps": [
    {"title": "Identify the hash", "desc": "A 32-hex-character value is MD5.",
     "cmd": "hashid hash.txt"},
    {"title": "Crack it with the wordlist", "desc": "Hashcat mode 0 is MD5. John works too if hashcat has no GPU.",
     "cmd": "hashcat -m 0 -a 0 hash.txt wordlist.txt --show\n# or:\njohn --format=raw-md5 --wordlist=wordlist.txt hash.txt"},
    {"title": "Wrap the cracked word", "desc": "Submit the recovered password as SIS{crackedword}.",
     "cmd": "hashcat -m 0 hash.txt --show"},
  ]},
 "11": {"time": "~10 min",
  "scenario": ("A second password hash turned up in the same dump, but it is a different algorithm. "
    "Confirm the type, then run the same style of dictionary attack against it."),
  "objective": "Identify the hash type, crack it against the wordlist; the cracked password is the flag.",
  "steps": [
    {"title": "Identify the hash", "desc": "A 40-hex-character value is SHA-1.",
     "cmd": "hashid hash.txt"},
    {"title": "Crack it with the wordlist", "desc": "Hashcat mode 100 is SHA-1 (or use John).",
     "cmd": "hashcat -m 100 -a 0 hash.txt wordlist.txt --show\n# or:\njohn --format=raw-sha1 --wordlist=wordlist.txt hash.txt"},
    {"title": "Wrap the cracked word", "desc": "Submit the recovered password as SIS{crackedword}.",
     "cmd": "hashcat -m 100 hash.txt --show"},
  ]},
 "12": {"time": "~7 min",
  "scenario": ("A wire-transfer instruction may have been altered in transit. A hash is a fingerprint of a "
    "file - change a single byte and the whole hash changes (the avalanche effect). Compare the two files "
    "with SHA-256 to prove whether one was tampered with and identify the altered field."),
  "objective": "Prove the files differ with SHA-256, identify the change, and unlock the flag.",
  "steps": [
    {"title": "Hash both files", "desc": "The two SHA-256 values will not match.",
     "cmd": "sha256sum original.txt tampered.txt"},
    {"title": "Find exactly what changed", "desc": "A single field (the amount) was altered.",
     "cmd": "diff original.txt tampered.txt"},
    {"title": "Unlock the flag", "desc": "Feed the SHA-256 of the tampered file to the unlocker.",
     "cmd": "python3 unlock.py <sha256-of-tampered.txt>"},
  ]},
}


# ==========================================================================
# Orchestration
# ==========================================================================
def main():
    ap = argparse.ArgumentParser(description="Generate the Module 20 Cryptography labs.")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--batch", default=None)
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(8), "big")
    rng = random.Random(seed)
    flags = Flags(rng)
    batch = args.batch or time.strftime("%Y%m%d") + f"-{seed & 0xffff:04x}"
    print(f"[*] Generating batch '{batch}' (seed={seed})")
    LAB.mkdir(exist_ok=True)

    # crack-lab passwords, hidden among decoys in a shared wordlist
    def pw():
        return rng.choice(BASE_WORDS) + str(rng.randint(1000, 9999))
    md5_pw, sha1_pw = pw(), pw()
    while sha1_pw == md5_pw:
        sha1_pw = pw()
    wl = "\n".join(build_wordlist(rng, [md5_pw, sha1_pw], size=600)) + "\n"
    for slug in ("10-md5-crack", "11-sha1-crack"):
        (CH / slug).mkdir(parents=True, exist_ok=True)
        write_text(CH / slug / "wordlist.txt", wl)

    steps = [
        ("01", "01-base64", "Base64 Decoding", "Section 1 - Encoding vs Encryption", 1,
         ["CyberChef", "base64"],
         "An API token that is Base64-encoded (twice). No key needed - decode it to read the data.",
         gen_base64),
        ("02", "02-hex", "Hex Decoding", "Section 1 - Encoding vs Encryption", 1,
         ["CyberChef", "xxd"],
         "A value stored as a hexadecimal string. Convert it straight back to readable text.",
         gen_hex),
        ("03", "03-binary", "Binary Decoding", "Section 1 - Encoding vs Encryption", 2,
         ["CyberChef", "python3"],
         "A raw bit-stream where every 8 bits is one ASCII character. Convert binary back to text.",
         gen_binary),
        ("04", "04-caesar", "Caesar Cipher", "Section 4 - Cryptographic Algorithms", 1,
         ["CyberChef", "python3"],
         "A note shifted with a Caesar cipher. Only 25 keys exist - brute-force them all.",
         gen_caesar),
        ("05", "05-atbash", "Atbash Cipher", "Section 4 - Cryptographic Algorithms", 1,
         ["CyberChef", "python3"],
         "A message hidden with Atbash (the alphabet reversed). Apply it again to decode.",
         gen_atbash),
        ("06", "06-vigenere", "Vigenere Cipher", "Section 4 - Cryptographic Algorithms", 2,
         ["CyberChef", "python3"],
         "A Vigenere-encrypted message. You have the keyword - use it to decrypt.",
         gen_vigenere),
        ("07", "07-aes-decrypt", "AES-256-CBC Decrypt", "Section 5 - Symmetric Key Cryptography", 2,
         ["openssl"],
         "An AES-256-CBC file with the key and IV supplied. Decrypt it with OpenSSL.",
         gen_aes),
        ("08", "08-rsa-decrypt", "RSA Decrypt (private key)", "Section 6 - Asymmetric Key Cryptography", 2,
         ["openssl"],
         "A file encrypted for an RSA public key. You hold the private key - decrypt it.",
         gen_rsa),
        ("09", "09-hybrid", "Hybrid Encryption (RSA + AES)", "Section 6 - Asymmetric Key Cryptography", 2,
         ["openssl"],
         "An RSA-wrapped AES key plus an AES-encrypted blob - the TLS pattern. Unwrap, then decrypt.",
         gen_hybrid),
        ("10", "10-md5-crack", "Hash Crack - MD5", "Section 7 - Hashing Algorithms", 2,
         ["hashid", "hashcat", "john"],
         "An MD5 password hash from a database dump. Identify it and crack it with the wordlist.",
         lambda r, f: gen_md5_crack(r, f, md5_pw)),
        ("11", "11-sha1-crack", "Hash Crack - SHA-1", "Section 7 - Hashing Algorithms", 2,
         ["hashid", "hashcat", "john"],
         "A SHA-1 password hash. Confirm the type and crack it with the wordlist.",
         lambda r, f: gen_sha1_crack(r, f, sha1_pw)),
        ("12", "12-integrity", "Integrity Check (SHA-256)", "Section 7 - Hashing Algorithms", 2,
         ["sha256sum", "python3"],
         "An original file and a possibly tampered copy. Use SHA-256 to prove what changed.",
         gen_integrity),
    ]

    batch_salt = os.urandom(16).hex()
    manifest = {"batch": batch, "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "salt": batch_salt, "pbkdf2_iters": PBKDF2_ITERS,
                "categories": CATEGORY_ORDER, "challenges": []}
    solutions = ["# Trainer Solutions - Module 20 Cryptography Labs\n",
                 f"**Batch:** `{batch}`  |  **Seed:** `{seed}`  |  {manifest['generated']}\n",
                 "> Keep this file OUT of the trainee bundle - it lists every flag.\n"]

    for cid, slug, title, section, diff, tools, brief, fn in steps:
        print(f"    - {cid} {title} ...", end=" ", flush=True)
        (CH / slug).mkdir(parents=True, exist_ok=True)   # openssl won't create -out dirs
        res = fn(rng, flags)
        hint = ""
        hp = CH / slug / "hint.txt"
        if hp.exists():
            hint = hp.read_text()
        g = GUIDES.get(cid, {})
        entry = {
            "id": cid, "slug": slug, "title": title, "section": section,
            "difficulty": diff, "tools": tools, "brief": brief,
            "files": res["files"], "hint": hint,
            "flag_pbkdf2": flag_hash(res["flag"], batch_salt),
            "category": CATEGORIES.get(cid, "Challenges"),
            "scenario": g.get("scenario", ""),
            "objective": g.get("objective", ""),
            "est_time": g.get("time", ""),
            "steps": g.get("steps", []),
        }
        manifest["challenges"].append(entry)
        solutions.append(f"\n## {cid} - {title}\n\n**Flag:** `{res['flag']}`\n\n{res['solution']}")
        print("ok")

    with open(LAB / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    write_text(ROOT / "trainer-solutions.md", "\n".join(solutions) + "\n")

    print(f"\n[+] Done. {len(steps)} labs generated.")
    print(f"[+] Manifest : {LAB / 'manifest.json'}")
    print(f"[+] Solutions: {ROOT / 'trainer-solutions.md'}  (do NOT ship)")
    print(f"[+] Start the lab with:  python3 Cryptography.py")


if __name__ == "__main__":
    main()
