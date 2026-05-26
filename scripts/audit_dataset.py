"""
scripts/audit_dataset.py
────────────────────────
Reads every image in dataset/efficientnet_b4 and dataset/scalp_yolo, then
prints:

  • image counts per class
  • aspect-ratio outliers (could indicate accidentally added screenshots)
  • size outliers (very small or huge)
  • corrupted / unreadable images (safe to skip during training)
  • duplicate filenames across classes (potential cross-contamination)

It NEVER modifies the dataset. It only reports.

Run:
    cd "/Users/alihassan/Desktop/fyp devlopment be"
    source venv/bin/activate
    python scripts/audit_dataset.py
"""
from __future__ import annotations
import os
import sys
from collections import defaultdict, Counter

from PIL import Image, UnidentifiedImageError

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKIN_TRAIN   = os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/train")
SKIN_VAL     = os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/val")
SCALP_IMG    = os.path.join(PROJECT_ROOT, "dataset/scalp_yolo/images")
SCALP_LBL    = os.path.join(PROJECT_ROOT, "dataset/scalp_yolo/labels")

EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def list_images(folder: str) -> list[str]:
    if not os.path.isdir(folder):
        return []
    out = []
    for fn in os.listdir(folder):
        ext = os.path.splitext(fn)[1].lower()
        if ext in EXT:
            out.append(os.path.join(folder, fn))
    return out


def audit_folder(name: str, root: str):
    if not os.path.isdir(root):
        print(f"\n• {name}: MISSING {root}")
        return
    print(f"\n━━ {name}  ({root}) ━━")
    classes = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    grand_total = 0
    bad = []
    aspect_outliers = []
    size_outliers   = []
    by_fname: dict[str, list[str]] = defaultdict(list)

    for cls in classes:
        files = list_images(os.path.join(root, cls))
        print(f"  {cls:<20s}  {len(files):>6d} images")
        grand_total += len(files)
        for fp in files:
            by_fname[os.path.basename(fp).lower()].append(cls)
            try:
                with Image.open(fp) as img:
                    w, h = img.size
                    ratio = max(w, h) / max(min(w, h), 1)
                    if ratio > 2.5:
                        aspect_outliers.append((fp, w, h, round(ratio, 2)))
                    if min(w, h) < 100 or max(w, h) > 5000:
                        size_outliers.append((fp, w, h))
            except (UnidentifiedImageError, OSError) as e:
                bad.append((fp, str(e)))

    print(f"  TOTAL:                {grand_total:>6d}")

    # Cross-class duplicate filename detection
    dupes = {f: cs for f, cs in by_fname.items() if len(set(cs)) > 1}
    if dupes:
        print(f"  ⚠ {len(dupes)} filenames appear in MORE than one class (sample of 5):")
        for f, cs in list(dupes.items())[:5]:
            print(f"     {f}  in classes: {sorted(set(cs))}")

    if bad:
        print(f"  ✗ {len(bad)} corrupted / unreadable images (first 3):")
        for fp, msg in bad[:3]:
            print(f"     {os.path.relpath(fp, PROJECT_ROOT)}  → {msg}")

    if aspect_outliers:
        print(f"  ⚠ {len(aspect_outliers)} aspect-ratio outliers (>2.5:1) — first 3:")
        for fp, w, h, r in aspect_outliers[:3]:
            print(f"     {os.path.relpath(fp, PROJECT_ROOT)}  {w}×{h} ratio {r}")

    if size_outliers:
        print(f"  ⚠ {len(size_outliers)} size outliers — first 3:")
        for fp, w, h in size_outliers[:3]:
            print(f"     {os.path.relpath(fp, PROJECT_ROOT)}  {w}×{h}")


def audit_scalp_yolo():
    print(f"\n━━ SCALP YOLO  ({SCALP_IMG}) ━━")
    if not os.path.isdir(SCALP_IMG):
        print("  MISSING")
        return
    for split in ("train", "val", "test"):
        img_dir = os.path.join(SCALP_IMG, split)
        lbl_dir = os.path.join(SCALP_LBL, split)
        if not os.path.isdir(img_dir):
            print(f"  [{split}] MISSING")
            continue
        imgs = list_images(img_dir)
        # Count YOLO class usage by reading labels
        class_count = Counter()
        empty_lbls = 0
        missing_lbls = 0
        for fp in imgs:
            name = os.path.splitext(os.path.basename(fp))[0]
            lbl_path = os.path.join(lbl_dir, name + ".txt")
            if not os.path.exists(lbl_path):
                missing_lbls += 1
                continue
            try:
                with open(lbl_path) as fh:
                    lines = [ln.strip() for ln in fh if ln.strip()]
                if not lines:
                    empty_lbls += 1
                    continue
                for ln in lines:
                    cid = int(ln.split()[0])
                    class_count[cid] += 1
            except Exception:
                pass
        print(f"  [{split}]  images={len(imgs)}  missing_lbls={missing_lbls}  empty_lbls={empty_lbls}")
        for cid in sorted(class_count):
            print(f"          class {cid}: {class_count[cid]} annotations")


def main():
    print("===================================================================")
    print("                        DATASET AUDIT")
    print("===================================================================")
    audit_folder("SKIN — TRAIN", SKIN_TRAIN)
    audit_folder("SKIN — VAL",   SKIN_VAL)
    audit_scalp_yolo()
    print("\n━━ Done. ━━")


if __name__ == "__main__":
    main()
