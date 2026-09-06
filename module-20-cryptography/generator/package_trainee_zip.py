#!/usr/bin/env python3
"""
Build the TRAINEE zip - the clean bundle you hand out.

It deliberately EXCLUDES:
  * generator/           (its source reveals the flag phrases -> brute-forceable)
  * trainer-solutions.md (every flag)
  * .lab/state.json      (progress; trainees start fresh)
  * __pycache__ / *.pyc  (build clutter)

It INCLUDES everything a trainee needs: Cryptography.py, README.md, setup/,
challenges/, and the portal's data files (.lab/manifest.json, .lab/bonus.enc).

Usage:
    python3 generator/package_trainee_zip.py            # writes to parent folder
    python3 generator/package_trainee_zip.py -o /path   # choose output dir
"""
import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP = "module-20-cryptography"   # top-level folder inside the zip

EXCLUDE_DIRS = {"generator", "__pycache__", "progress"}   # progress/ = per-user runtime data
EXCLUDE_FILES = {"trainer-solutions.md", "hint.txt"}      # Quick hint lives in the portal instead
# runtime state that must NOT ship (created when the trainer runs the portal)
EXCLUDE_LAB = {"state.json", "state.tmp", "users.json", "sessions.json",
               "users.tmp", "sessions.tmp"}
EXCLUDE_SUFFIX = {".pyc", ".tmp", ".zip"}


def included(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if any(p in EXCLUDE_DIRS for p in parts):
        return False
    if rel.name in EXCLUDE_FILES:
        return False
    if path.suffix in EXCLUDE_SUFFIX:
        return False
    if parts and parts[0] == ".lab" and rel.name in EXCLUDE_LAB:
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--outdir", default=str(ROOT.parent),
                    help="directory to write the zip into (default: parent folder)")
    args = ap.parse_args()

    batch = "unknown"
    mani = ROOT / ".lab" / "manifest.json"
    if mani.exists():
        batch = json.load(open(mani)).get("batch", "unknown")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    zip_path = outdir / f"{TOP}-trainee-{batch}.zip"

    n = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ROOT.rglob("*")):
            if path.is_dir():
                continue
            if not included(path):
                continue
            arc = Path(TOP) / path.relative_to(ROOT)
            z.write(path, arc.as_posix())
            n += 1

    print(f"[+] Trainee bundle: {zip_path}")
    print(f"[+] {n} files, {zip_path.stat().st_size // 1024} KB")
    print(f"[+] Excluded: generator/, trainer-solutions.md, state, caches")
    print(f"[+] Keep trainer-solutions.md ({ROOT / 'trainer-solutions.md'}) for yourself.")


if __name__ == "__main__":
    main()
