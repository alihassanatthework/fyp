"""
scripts/dedupe_skin_milia.py
────────────────────────────
Removes the `milia-*.jpg` duplicates that exist in BOTH `acne/` AND
`dark_spots/` (train + val).

Strategy: milia (small benign cysts) is more often described as a
pigmentation / spot lesion than as acne. We KEEP `dark_spots/milia-*.jpg`
and REMOVE `acne/milia-*.jpg`. Use --keep acne to flip the decision.

Dry-run by default. Pass --apply to actually delete.

Run:
    cd "/Users/alihassan/Desktop/fyp devlopment be"
    source venv/bin/activate
    python scripts/dedupe_skin_milia.py           # dry-run preview
    python scripts/dedupe_skin_milia.py --apply   # actually delete
"""
from __future__ import annotations
import argparse
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOTS = [
    os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/train"),
    os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/val"),
]

def find_duplicates(root: str) -> list[tuple[str, str]]:
    acne_dir = os.path.join(root, "acne")
    dark_dir = os.path.join(root, "dark_spots")
    if not (os.path.isdir(acne_dir) and os.path.isdir(dark_dir)):
        return []
    acne_files = {f.lower(): f for f in os.listdir(acne_dir)}
    dark_files = {f.lower(): f for f in os.listdir(dark_dir)}
    common = sorted(set(acne_files) & set(dark_files))
    return [(os.path.join(acne_dir, acne_files[c]),
             os.path.join(dark_dir, dark_files[c])) for c in common]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually delete (otherwise dry-run)")
    ap.add_argument("--keep", choices=("acne", "dark_spots"), default="dark_spots",
                    help="Which class to KEEP the milia samples in (default: dark_spots)")
    args = ap.parse_args()

    total_removed = 0
    for root in ROOTS:
        dupes = find_duplicates(root)
        if not dupes:
            print(f"• {root}: no duplicates")
            continue
        print(f"\n• {root}: {len(dupes)} duplicate file pair(s)")
        for acne_p, dark_p in dupes:
            target = acne_p if args.keep == "dark_spots" else dark_p
            kept   = dark_p if args.keep == "dark_spots" else acne_p
            print(f"   keep  → {os.path.relpath(kept, PROJECT_ROOT)}")
            print(f"   remove→ {os.path.relpath(target, PROJECT_ROOT)}")
            if args.apply:
                try:
                    os.remove(target)
                    total_removed += 1
                except OSError as e:
                    print(f"     ✗ {e}")

    if args.apply:
        print(f"\n✓ Removed {total_removed} file(s).")
    else:
        print("\n(dry-run; re-run with --apply to actually delete)")

if __name__ == "__main__":
    main()
