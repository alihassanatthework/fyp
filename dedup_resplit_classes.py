"""
dedup_resplit_classes.py
────────────────────────
For the enlarged consolidated classes only:
    dataset/efficientnet_b4/{acne, dryness_new, dark_spots, normal}

Step 1  Dedup WITHIN each class (exact SHA-1 + perceptual near-dup, pHash
        Hamming ≤ 6). Cross-class duplicates are NOT touched (we only ever
        compare images inside the same class). Removes the overlap the
        IMG_CLASSES merge introduced.

Step 2  Re-split each class 80/20 stratified at the disease-subfolder level,
        redistributing ALL surviving images (merged ones included). Disease
        subfolder structure preserved inside train/ and val/.

Guards:
  • Touches ONLY the four class folders above.
  • Never touches efficientnet_b4/train, efficientnet_b4/val, or scalp_yolo.
  • Move-based (no copies); staging dir prevents train↔val name collisions.

Usage:
    source venv/bin/activate
    python dedup_resplit_classes.py
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import time
from collections import defaultdict
from typing import Dict, List

import numpy as np
import cv2

EFF        = "dataset/efficientnet_b4"
CLASSES    = ["acne", "dryness_new", "dark_spots", "normal"]
DATA_EXTS  = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
NEAR_THRESH = 6
VAL_FRAC   = 0.20
SEED       = 42

EFF_ABS = os.path.abspath(EFF)
SCALP   = os.path.abspath("dataset/scalp_yolo")
PROTECTED = {os.path.abspath(f"{EFF}/train"), os.path.abspath(f"{EFF}/val")}


def guard(path: str):
    ap = os.path.abspath(path)
    if ap.startswith(SCALP):
        raise RuntimeError(f"REFUSED (scalp_yolo): {path}")
    for p in PROTECTED:
        if ap == p or ap.startswith(p + os.sep):
            raise RuntimeError(f"REFUSED (protected train/val): {path}")
    if not ap.startswith(EFF_ABS):
        raise RuntimeError(f"REFUSED (outside efficientnet_b4): {path}")


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


def collect(class_dir: str):
    """Return dict: subfolder -> list of current file paths (across train+val).
    subfolder '' means class root (normal)."""
    by_sub: Dict[str, List[str]] = defaultdict(list)
    for split in ('train', 'val'):
        sdir = os.path.join(class_dir, split)
        if not os.path.isdir(sdir):
            continue
        for cur, _d, files in os.walk(sdir):
            sub = os.path.relpath(cur, sdir)
            sub = '' if sub == '.' else sub
            for f in sorted(files):
                if f.lower().endswith(DATA_EXTS):
                    by_sub[sub].append(os.path.join(cur, f))
    return by_sub


def main():
    t0 = time.time()
    report = {'classes': {}}

    for cls in CLASSES:
        cdir = os.path.join(EFF, cls)
        if not os.path.isdir(cdir):
            print(f"⚠ missing class: {cdir}")
            continue
        guard(cdir)
        print(f"\n══ {cls} ══")
        by_sub = collect(cdir)
        n0 = sum(len(v) for v in by_sub.values())
        print(f"  collected {n0} images across {len(by_sub)} subfolder(s)")

        # ── Step 1: dedup within class (across all subfolders) ──
        seen_sha = set()
        kept_mat = []                      # pHash of survivors
        survivors: Dict[str, List[str]] = defaultdict(list)
        n_exact = n_near = 0
        # deterministic processing order
        ordered = [(sub, p) for sub in sorted(by_sub) for p in by_sub[sub]]
        for sub, p in ordered:
            try:
                s = sha1(p)
            except OSError:
                continue
            if s in seen_sha:
                guard(p); os.remove(p); n_exact += 1
                continue
            seen_sha.add(s)
            h = phash(p)
            if h is not None and kept_mat:
                mat = np.array(kept_mat)
                if int(np.count_nonzero(mat != h, axis=1).min()) <= NEAR_THRESH:
                    guard(p); os.remove(p); n_near += 1
                    continue
            if h is not None:
                kept_mat.append(h)
            survivors[sub].append(p)

        n_surv = sum(len(v) for v in survivors.values())
        print(f"  dedup: exact={n_exact}  near={n_near}  survivors={n_surv}")

        # ── Step 2: stage then re-split 80/20 per subfolder ──
        staging = os.path.join(cdir, '_staging')
        guard(staging)
        if os.path.exists(staging):
            shutil.rmtree(staging)
        os.makedirs(staging)
        # move survivors to staging/<sub>/ (collision-safe)
        for sub, paths in survivors.items():
            sdir = os.path.join(staging, sub) if sub else staging
            os.makedirs(sdir, exist_ok=True)
            seen = set()
            for p in paths:
                base = os.path.basename(p)
                name = base
                if name in seen:
                    stem, ext = os.path.splitext(base)
                    k = 1; name = f"{stem}__d{ext}"
                    while name in seen:
                        name = f"{stem}__d{k}{ext}"; k += 1
                seen.add(name)
                shutil.move(p, os.path.join(sdir, name))

        # wipe old train/ val/, rebuild from staging
        for split in ('train', 'val'):
            sp = os.path.join(cdir, split)
            if os.path.isdir(sp):
                guard(sp); shutil.rmtree(sp)

        sub_counts = {}
        cls_tr = cls_va = 0
        for sub in sorted(survivors):
            sdir = os.path.join(staging, sub) if sub else staging
            files = [os.path.join(sdir, f) for f in sorted(os.listdir(sdir))
                     if f.lower().endswith(DATA_EXTS)]
            rng = random.Random(SEED + len(files))
            rng.shuffle(files)
            n_val = int(round(len(files) * VAL_FRAC))
            val_files, train_files = files[:n_val], files[n_val:]
            for split, group in (('train', train_files), ('val', val_files)):
                dst = os.path.join(cdir, split, sub) if sub else os.path.join(cdir, split)
                os.makedirs(dst, exist_ok=True)
                for fp in group:
                    shutil.move(fp, os.path.join(dst, os.path.basename(fp)))
            sub_counts[sub or '(root)'] = {'train': len(train_files), 'val': len(val_files)}
            cls_tr += len(train_files); cls_va += len(val_files)

        shutil.rmtree(staging)

        report['classes'][cls] = {
            'before': n0, 'exact_removed': n_exact, 'near_removed': n_near,
            'after': n_surv, 'train': cls_tr, 'val': cls_va,
            'subfolders': sub_counts,
        }
        print(f"  re-split: train={cls_tr}  val={cls_va}")

    report['elapsed_sec'] = round(time.time() - t0, 1)
    os.makedirs('reorg_4class_report', exist_ok=True)
    with open('reorg_4class_report/dedup_resplit_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    # ── Summary ──
    print("\n══ SUMMARY ══")
    print(f"{'class':14s} {'before':>7} {'exact':>6} {'near':>6} {'after':>7} {'train':>7} {'val':>6}")
    for cls in CLASSES:
        r = report['classes'].get(cls)
        if not r: continue
        print(f"{cls:14s} {r['before']:>7} {r['exact_removed']:>6} "
              f"{r['near_removed']:>6} {r['after']:>7} {r['train']:>7} {r['val']:>6}")
    print(f"\n✅ Done in {report['elapsed_sec']}s")
    print("📝 reorg_4class_report/dedup_resplit_report.json")


if __name__ == '__main__':
    main()
