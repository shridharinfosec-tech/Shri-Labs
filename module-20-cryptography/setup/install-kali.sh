#!/usr/bin/env bash
# SIS Module 20 Crypto CTF - installer for Kali / Ubuntu / Debian.
# Installs everything the lab needs. Safe to re-run.
#
#   bash setup/install-kali.sh
#
set -e

if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
else
  SUDO=""
fi

echo "[*] Updating package lists..."
$SUDO apt-get update -y

echo "[*] Installing core tools (python3, openssl, coreutils, xxd)..."
$SUDO apt-get install -y python3 openssl coreutils xxd

echo "[*] Installing hash tools (hashcat, john, hashid)..."
# On Kali these are usually present already; on Ubuntu they come from the repos.
$SUDO apt-get install -y hashcat john hashid || {
  echo "[!] 'hashid' package not found via apt; trying pip..."
  $SUDO apt-get install -y python3-pip || true
  pip3 install hashid || pip3 install --break-system-packages hashid || true
}

echo
echo "[+] Done. Verifying..."
bash "$(dirname "$0")/check-tools.sh" || true

echo
echo "Notes:"
echo " - hashcat needs a working OpenCL/GPU driver for full speed, but these small"
echo "   lab hashes crack fine on CPU. If hashcat complains about no devices, add"
echo "   --force, or just use John the Ripper instead (john --wordlist=... hash.txt)."
echo " - No internet is required to SOLVE any challenge."
