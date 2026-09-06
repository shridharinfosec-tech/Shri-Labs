#!/usr/bin/env bash
# SIS Module 20 Crypto CTF - environment checker.
# Tells you which tools are present and which challenges each one is needed for.
# Run:  bash setup/check-tools.sh

green(){ printf "  \033[32m[ OK ]\033[0m %-22s %s\n" "$1" "$2"; }
red(){   printf "  \033[31m[MISS]\033[0m %-22s %s\n" "$1" "$2"; }

check(){  # $1=cmd  $2=note
  if command -v "$1" >/dev/null 2>&1; then green "$1" "$2"; else red "$1" "$2"; MISSING=1; fi
}
either(){ # $1=cmd1 $2=cmd2 $3=note
  if command -v "$1" >/dev/null 2>&1 || command -v "$2" >/dev/null 2>&1; then
    green "$1/$2" "$3"
  else red "$1/$2" "$3"; MISSING=1; fi
}

echo "SIS Module 20 - Cryptography CTF : tool check"
echo "--------------------------------------------------------------"
MISSING=0
check python3   "the lab portal + challenges 3,4,7,10"
check openssl   "challenges 2, 5, 8, 9, 11"
check base64    "challenge 11 (coreutils)"
check xxd       "handy for 3, 5 (vim-common)"
check sha256sum "challenge 7 (coreutils)"
check sha1sum   "handy for 6 (coreutils)"
either hashid hash-identifier "challenges 6, 11 (identify a hash)"
either hashcat john           "challenges 6, 11 (crack a hash)"
echo "--------------------------------------------------------------"
if [ "$MISSING" = "1" ]; then
  echo "Some tools are missing. On Kali/Ubuntu run:  bash setup/install-kali.sh"
  exit 1
else
  echo "All set. Start the lab with:  python3 Cryptography.py"
fi
