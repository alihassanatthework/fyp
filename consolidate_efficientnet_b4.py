"""
consolidate_efficientnet_b4.py
──────────────────────────────
Consolidate the new 4-class structure into dataset/efficientnet_b4/ and
clean redundant material. Scope confirmed by the user:

  STEP 2  Move new top-level folders into efficientnet_b4/:
            dataset/acne        → dataset/efficientnet_b4/acne
            dataset/dark_spots  → dataset/efficientnet_b4/dark_spots
            dataset/normal      → dataset/efficientnet_b4/normal
            dataset/dryness     → dataset/efficientnet_b4/dryness_new   (renamed)

  STEP 3  Delete ONLY fully-duplicated old material ("safe only"):
            dermnet_dataset/                              (100% consumed)
            IMG_CLASSES/5. Melanocytic Nevi (NV) - 7970  (→ dark_spots)
            IMG_CLASSES/6. Benign Keratosis-like Lesions (BKL) 2624 (→ dark_spots)
            train/normal, val/normal                     (→ normal)
          KEEP all unique data (acne_dataset, data_eczema, other IMG_CLASSES,
          old train/val acne+dark_spots+dryness).

  STEP 4  Image-level dedup WITHIN each new class folder (exact SHA-1 +
          perceptual near-dup). Cross-class duplicates are kept (we only
          dedup inside a single top-level class). Train copies are kept in
          preference to val copies, which removes train↔val leakage.

Guards:
  • Operates only under dataset/efficientnet_b4/.
  • Never touches dataset/scalp_yolo/.
  • There is no efficientnet_b4/dryness/ binary folder anymore (user confirmed).

Usage:
    source venv/bin/activate
    python consolidate_efficientnet_b4.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from typing import List

import numpy as np
import cv2

EFF        = "dataset/efficientnet_b4"
DATA_EXTS  = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
NEAR_THRESH = 6
NEW_CLASSES = ["acne", "dryness_new", "dark_spots", "normal"]

MOVES = [
    ("dataset/acne",       f"{EFF}/acne"),
    ("dataset/dark_spots", f"{EFF}/dark_spots"),
    ("dataset/normal",     f"{EFF}/normal"),
    ("dataset/dryness",    f"{EFF}/dryness_new"),
]

DELETE_SAFE = [
    f"{EFF}/dermnet_dataset",
    f"{EFF}/IMG_CLASSES/5. Melanocytic Nevi (NV) - 7970",
    f"{EFF}/IMG_CLASSES/6. Benign Keratosis-like Lesions (BKL) 2624",
    f"{EFF}/train/normal",
    f"{EFF}/val/normal",
]

# Absolute guard — refuse to operate outside efficientnet_b4 or inside scalp_yolo.
SCALP = os.path.abspath("dataset/scalp_yolo")
EFF_ABS = os.path.abspath(EFF)


def guard(path: str):
    ap = os.path.abspath(path)
    if ap.startswith(SCALP):
        raise RuntimeError(f"REFUSED (scalp_yolo): {path}")
    if not ap.startswith(EFF_ABS):
        raise RuntimeError(f"REFUSED (outside efficientnet_b4): {path}")


def list_images(folder: str) -> List[str]:
    out = []
    for cur, _dirs, files in os.walk(folder):
        for f in sorted(files):
            if f.lower().endswith(DATA_EXTS):
                out.append(os.path.join(cur, f))
    return out


def sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def phash(path: str):
    img = cv2.imread(path)
    if img is None:
        return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g32 = cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(g32)
    low = dct[:8, :8]
    med = np.median(low[1:])
    return (low > med).flatten().astype(np.uint8)


def ordered_class_images(class_dir: str) -> List[str]:
    """train images first, then val — so train copies win during dedup."""
    tr = list_images(os.path.join(class_dir, 'train'))
    va = list_images(os.path.join(class_dir, 'val'))
    other = [p for p in list_images(class_dir)
             if p not in tr and p not in va]
    return tr + va + other


def main():
    t0 = time.time()
    report = {'moved': [], 'deleted_folders': [], 'dedup': {}, 'final_counts': {}}

    # ── STEP 2 — moves ──
    print("══ STEP 2 ══ Move new folders into efficientnet_b4/")
    for src, dst in MOVES:
        if not os.path.isdir(src):
            print(f"  ⚠ source missing, skipped: {src}")
            report['moved'].append({'src': src, 'dst': dst, 'status': 'missing'})
            continue
        guard(dst)
        if os.path.exists(dst):
            print(f"  ⚠ destination exists, skipped: {dst}")
            report['moved'].append({'src': src, 'dst': dst, 'status': 'dst_exists'})
            continue
        shutil.move(src, dst)
        print(f"  ✓ {src}  →  {dst}")
        report['moved'].append({'src': src, 'dst': dst, 'status': 'moved'})

    # ── STEP 3 — safe deletes ──
    print("\n══ STEP 3 ══ Delete fully-duplicated old folders (safe only)")
    for d in DELETE_SAFE:
        guard(d)
        if os.path.isdir(d):
            n = len(list_images(d))
            shutil.rmtree(d)
            print(f"  ✓ deleted {d}  ({n} images)")
            report['deleted_folders'].append({'path': d, 'images': n})
        else:
            print(f"  ⚠ not found, skipped: {d}")
            report['deleted_folders'].append({'path': d, 'images': 0,
                                               'status': 'missing'})

    # ── STEP 4 — image dedup within each new class ──
    print("\n══ STEP 4 ══ Image dedup within each new class")
    total_exact = total_near = 0
    for cls in NEW_CLASSES:
        cdir = os.path.join(EFF, cls)
        if not os.path.isdir(cdir):
            print(f"  ⚠ class folder missing: {cdir}")
            continue
        imgs = ordered_class_images(cdir)
        n0 = len(imgs)

        # exact dedup
        seen_sha = set()
        survivors = []
        n_exact = 0
        for p in imgs:
            try:
                s = sha1(p)
            except OSError:
                continue
            if s in seen_sha:
                guard(p); os.remove(p); n_exact += 1
            else:
                seen_sha.add(s); survivors.append(p)

        # near dedup (pHash) on survivors, train-first order preserved
        kept_mat = []
        n_near = 0
        for p in survivors:
            h = phash(p)
            if h is None:
                continue
            if kept_mat:
                mat = np.array(kept_mat)
                dmin = int(np.count_nonzero(mat != h, axis=1).min())
                if dmin <= NEAR_THRESH:
                    guard(p); os.remove(p); n_near += 1
                    continue
            kept_mat.append(h)

        n_final = n0 - n_exact - n_near
        total_exact += n_exact; total_near += n_near
        report['dedup'][cls] = {'before': n0, 'exact_removed': n_exact,
                                 'near_removed': n_near, 'after': n_final}
        print(f"  {cls:12s} before={n0:>6}  exact-dup={n_exact:>5}  "
              f"near-dup={n_near:>5}  after={n_final:>6}")

    # ── Final counts ──
    print("\n══ FINAL counts per class (train/val) ══")
    for cls in NEW_CLASSES:
        cdir = os.path.join(EFF, cls)
        tr = len(list_images(os.path.join(cdir, 'train')))
        va = len(list_images(os.path.join(cdir, 'val')))
        report['final_counts'][cls] = {'train': tr, 'val': va, 'total': tr + va}
        print(f"  {cls:12s} train={tr:>6}  val={va:>5}  total={tr+va:>6}")

    report['total_exact_removed'] = total_exact
    report['total_near_removed']  = total_near
    report['elapsed_sec'] = round(time.time() - t0, 1)

    os.makedirs('reorg_4class_report', exist_ok=True)
    with open('reorg_4class_report/consolidate_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Done in {report['elapsed_sec']}s")
    print(f"   exact dups removed: {total_exact}   near dups removed: {total_near}")
    print(f"📝 reorg_4class_report/consolidate_report.json")


if __name__ == '__main__':
    main()
