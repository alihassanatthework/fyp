"""
phase0_verify_and_testsplit.py
──────────────────────────────
Phase 0 for the primary 4-class model. NO training. NO .pth touched.

Scope: dataset/efficientnet_b4/{acne, dryness_new, dark_spots, normal}

Part A — VERIFY (read-only):
  • per-class / per-split counts
  • corrupted-file scan (sampled)
  • residual train↔val near-duplicate leakage check (pHash, sampled) to
    confirm the earlier dedup held

Part B — CARVE TEST SPLIT (moves files):
  • test = 50% of the current val set, stratified per disease subfolder
    → final ratio ≈ 80 / 10 / 10 (train / val / test)
  • train is left untouched (max training data)
  • disease subfolder structure preserved inside test/

Guards:
  • only the 4 class folders are touched
  • never reads/writes scalp_yolo or any *.pth
  • deterministic (seed 42)

Usage:
    source venv/bin/activate
    python phase0_verify_and_testsplit.py            # verify + carve
    python phase0_verify_and_testsplit.py --verify-only
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import time
from collections import defaultdict
from typing import Dict, List

import numpy as np
import cv2

EFF       = "dataset/efficientnet_b4"
CLASSES   = ["acne", "dryness_new", "dark_spots", "normal"]
DATA_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
TEST_FRAC_OF_VAL = 0.50
SEED      = 42
NEAR_THRESH = 6

EFF_ABS = os.path.abspath(EFF)
SCALP   = os.path.abspath("dataset/scalp_yolo")


def guard(path: str):
    ap = os.path.abspath(path)
    if ap.startswith(SCALP):
        raise RuntimeError(f"REFUSED (scalp): {path}")
    if ap.endswith('.pth'):
        raise RuntimeError(f"REFUSED (.pth): {path}")
    if not ap.startswith(EFF_ABS):
        raise RuntimeError(f"REFUSED (outside eff): {path}")


def images_under(folder: str) -> List[str]:
    out = []
    if not os.path.isdir(folder):
        return out
    for cur, _d, files in os.walk(folder):
        for f in sorted(files):
            if f.lower().endswith(DATA_EXTS):
                out.append(os.path.join(cur, f))
    return out


def subfolder_map(split_dir: str) -> Dict[str, List[str]]:
    by = defaultdict(list)
    if not os.path.isdir(split_dir):
        return by
    for cur, _d, files in os.walk(split_dir):
        sub = os.path.relpath(cur, split_dir)
        sub = '' if sub == '.' else sub
        for f in sorted(files):
            if f.lower().endswith(DATA_EXTS):
                by[sub].append(os.path.join(cur, f))
    return by


def phash(path: str):
    img = cv2.imread(path)
    if img is None:
        return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g32 = cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(g32)
    low = dct[:8, :8]
    return (low > np.median(low[1:])).flatten().astype(np.uint8)


def leak_check(class_dir, sample=250):
    """Sampled pHash check: how many val images near-duplicate a train image."""
    tr = images_under(os.path.join(class_dir, 'train'))
    va = images_under(os.path.join(class_dir, 'val'))
    if not tr or not va:
        return {'val_sampled': 0, 'near_dup': 0, 'pct': 0.0}
    rng = random.Random(SEED)
    tr_s = rng.sample(tr, min(len(tr), 1500))
    va_s = rng.sample(va, min(len(va), sample))
    tr_mat = np.array([h for h in (phash(p) for p in tr_s) if h is not None])
    hits = 0
    for p in va_s:
        h = phash(p)
        if h is None or tr_mat.size == 0:
            continue
        if int(np.count_nonzero(tr_mat != h, axis=1).min()) <= NEAR_THRESH:
            hits += 1
    return {'val_sampled': len(va_s), 'near_dup': hits,
            'pct': round(100 * hits / max(1, len(va_s)), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify-only', action='store_true')
    args = ap.parse_args()
    t0 = time.time()
    report = {'verify': {}, 'carve': {}, 'final': {}}

    # ── PART A: VERIFY ──
    print("══ PART A ══ Verify clean data (read-only)\n")
    for cls in CLASSES:
        cdir = os.path.join(EFF, cls)
        tr = images_under(os.path.join(cdir, 'train'))
        va = images_under(os.path.join(cdir, 'val'))
        # corrupt scan (sampled)
        rng = random.Random(SEED)
        sample = rng.sample(tr + va, min(300, len(tr) + len(va)))
        corrupt = [p for p in sample if cv2.imread(p) is None]
        leak = leak_check(cdir)
        report['verify'][cls] = {
            'train': len(tr), 'val': len(va),
            'corrupt_in_sample': len(corrupt),
            'sample_size': len(sample),
            'val_train_leak_pct': leak['pct'],
            'leak_detail': leak,
        }
        print(f"  {cls:12s} train={len(tr):>6} val={len(va):>5} | "
              f"corrupt {len(corrupt)}/{len(sample)} | "
              f"val→train leak {leak['pct']}% ({leak['near_dup']}/{leak['val_sampled']})")

    if args.verify_only:
        with open('reorg_4class_report/phase0_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print("\n🧪 verify-only — no files moved.")
        return

    # ── PART B: CARVE TEST (move 50% of val → test, per subfolder) ──
    print(f"\n══ PART B ══ Carve test = {int(TEST_FRAC_OF_VAL*100)}% of val "
          "(stratified per subfolder)\n")
    for cls in CLASSES:
        cdir = os.path.join(EFF, cls)
        val_by = subfolder_map(os.path.join(cdir, 'val'))
        moved = 0
        for sub, files in val_by.items():
            rng = random.Random(SEED + len(files))
            files = sorted(files)
            rng.shuffle(files)
            n_test = int(round(len(files) * TEST_FRAC_OF_VAL))
            test_files = files[:n_test]
            dst = os.path.join(cdir, 'test', sub) if sub else os.path.join(cdir, 'test')
            guard(dst)
            os.makedirs(dst, exist_ok=True)
            for p in test_files:
                guard(p)
                shutil.move(p, os.path.join(dst, os.path.basename(p)))
                moved += 1
        report['carve'][cls] = {'moved_to_test': moved}
        print(f"  {cls:12s} moved {moved} val→test")

    # ── FINAL counts ──
    print("\n══ FINAL train/val/test counts ══")
    grand = {'train': 0, 'val': 0, 'test': 0}
    for cls in CLASSES:
        cdir = os.path.join(EFF, cls)
        c = {sp: len(images_under(os.path.join(cdir, sp))) for sp in ('train', 'val', 'test')}
        report['final'][cls] = c
        for k in grand: grand[k] += c[k]
        tot = sum(c.values())
        print(f"  {cls:12s} train={c['train']:>6} ({c['train']/tot*100:4.1f}%) "
              f"val={c['val']:>5} ({c['val']/tot*100:4.1f}%) "
              f"test={c['test']:>5} ({c['test']/tot*100:4.1f}%)  total={tot}")
    report['final']['_grand'] = grand
    print(f"\n  GRAND  train={grand['train']} val={grand['val']} test={grand['test']}")
    mx, mn = max(grand_c := [report['final'][c]['train']+report['final'][c]['val']+report['final'][c]['test'] for c in CLASSES]), min(grand_c)
    print(f"  class imbalance (total): {mx/mn:.2f}×")
    report['imbalance_total'] = mx / mn
    report['elapsed_sec'] = round(time.time() - t0, 1)

    os.makedirs('reorg_4class_report', exist_ok=True)
    with open('reorg_4class_report/phase0_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n✅ Phase 0 done in {report['elapsed_sec']}s — NO training, NO .pth touched.")
    print("📝 reorg_4class_report/phase0_report.json")


if __name__ == '__main__':
    main()
