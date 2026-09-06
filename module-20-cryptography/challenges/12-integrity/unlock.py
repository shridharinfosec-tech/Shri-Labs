#!/usr/bin/env python3
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
