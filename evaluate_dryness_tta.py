"""
evaluate_dryness_tta.py
───────────────────────
Option B — squeeze more accuracy out of core/ai_models/dryness_v2.pth
WITHOUT retraining and WITHOUT modifying the .pth file.

What this does:
  1. Loads the trained dryness_v2.pth (read-only, never written to).
  2. Baseline evaluation on the held-out test set (single forward, threshold 0.5).
  3. Test-Time Augmentation (TTA) — runs each test image through the model
     5 times with light augmentations (original, hflip, rot+10°, rot-10°,
     brightness +0.15) and averages the softmax probabilities. This smooths
     out noisy single-view predictions.
  4. Threshold tuning — sweeps decision thresholds for P(dry) on the
     VALIDATION set (so the test set stays untouched), picks the threshold
     that maximises (a) F1 of the dry class and (b) overall accuracy.
  5. Applies the chosen threshold to the TTA probabilities on the test set
     and reports the final improved metrics.
  6. Writes the chosen calibration (TTA flag + threshold) to
        core/ai_models/dryness_v2_calibration.json
     so inference code can pick it up later. The .pth itself is never
     modified.

Run from project root (uses your venv + MPS):

    source venv/bin/activate
    python evaluate_dryness_tta.py --device mps
"""

from __future__ import annotations

import argparse
import json
import os
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torchvision.models import efficientnet_b4
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    roc_auc_score, confusion_matrix,
)
from tqdm import tqdm


# ── Paths ───────────────────────────────────────────────────────────
WEIGHTS_PATH   = "core/ai_models/dryness_v2.pth"
DATASET_ROOT   = "dataset/efficientnet_b4/dryness"
VAL_DIR        = f"{DATASET_ROOT}/val"
TEST_DIR       = f"{DATASET_ROOT}/test"
CALIB_OUT      = "core/ai_models/dryness_v2_calibration.json"


# ── Device pick ─────────────────────────────────────────────────────
def pick_device(name: str) -> torch.device:
    if name == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    if name == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# ── Model loader (matches train_dryness_v2.py architecture) ─────────
def load_model(device: torch.device):
    ckpt = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=False)
    classes  = ckpt["classes"]                      # ['dry', 'not_dry']
    img_size = ckpt.get("img_size", 224)
    mean     = tuple(ckpt.get("normalize_mean", (0.485, 0.456, 0.406)))
    std      = tuple(ckpt.get("normalize_std",  (0.229, 0.224, 0.225)))

    model = efficientnet_b4(weights=None)
    in_feat = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_feat, len(classes)),
    )
    model.load_state_dict(ckpt["state_dict"])
    model.to(device).eval()

    dry_idx = classes.index("dry")
    print(f"✓ Loaded {WEIGHTS_PATH}")
    print(f"  classes   : {classes}  (dry index = {dry_idx})")
    print(f"  img_size  : {img_size}")
    print(f"  best train val_acc (in ckpt): {ckpt.get('best_val_acc', 'n/a')}")
    return model, classes, img_size, mean, std, dry_idx


# ── Eval transforms ─────────────────────────────────────────────────
def base_eval_transform(img_size, mean, std):
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])


def tta_transforms(img_size, mean, std):
    """5 light augmentations. Each returns a Compose."""
    norm = transforms.Normalize(mean, std)
    to_t = transforms.ToTensor()
    resize = transforms.Resize((img_size, img_size))

    return [
        # 1) original
        transforms.Compose([resize, to_t, norm]),
        # 2) horizontal flip
        transforms.Compose([resize, transforms.RandomHorizontalFlip(p=1.0), to_t, norm]),
        # 3) rotate +10
        transforms.Compose([resize, transforms.RandomRotation((10, 10)), to_t, norm]),
        # 4) rotate -10
        transforms.Compose([resize, transforms.RandomRotation((-10, -10)), to_t, norm]),
        # 5) brightness +0.15
        transforms.Compose([resize, transforms.ColorJitter(brightness=(1.15, 1.15)), to_t, norm]),
    ]


# ── Probability collectors ──────────────────────────────────────────
@torch.no_grad()
def collect_probs(model, loader, device) -> Tuple[np.ndarray, np.ndarray]:
    """Single-pass forward. Returns (probs[N,2], targets[N])."""
    all_p, all_y = [], []
    for imgs, ys in tqdm(loader, ncols=100, desc="forward"):
        imgs = imgs.to(device)
        logits = model(imgs)
        probs = F.softmax(logits, dim=1).cpu().numpy()
        all_p.append(probs)
        all_y.extend(ys.numpy().tolist())
    return np.concatenate(all_p, axis=0), np.array(all_y)


@torch.no_grad()
def collect_probs_tta(model, dataset_dir, tta_list, batch_size, workers,
                       device) -> Tuple[np.ndarray, np.ndarray]:
    """Runs the entire dataset N times (one per TTA transform) and
    averages the softmax outputs across the N runs.
    Returns (avg_probs[N,2], targets[N])."""
    probs_sum = None
    targets   = None
    for i, tf in enumerate(tta_list, start=1):
        ds = datasets.ImageFolder(dataset_dir, transform=tf)
        ld = DataLoader(ds, batch_size=batch_size, shuffle=False,
                         num_workers=workers, pin_memory=False)
        p, y = collect_probs(model, ld, device)
        if probs_sum is None:
            probs_sum = p
            targets   = y
        else:
            probs_sum = probs_sum + p
        print(f"   ✓ TTA pass {i}/{len(tta_list)}")
    avg = probs_sum / len(tta_list)
    return avg, targets


# ── Metric helpers ─────────────────────────────────────────────────
def metrics_at_threshold(probs: np.ndarray, y_true: np.ndarray,
                          dry_idx: int, threshold: float) -> dict:
    """Decision rule: predict 'dry' iff P(dry) > threshold."""
    p_dry = probs[:, dry_idx]
    y_pred = np.where(p_dry > threshold, dry_idx, 1 - dry_idx)
    acc = accuracy_score(y_true, y_pred)
    p, r, f, _ = precision_recall_fscore_support(
        y_true, y_pred, pos_label=dry_idx, average='binary', zero_division=0)
    try:
        # AUC uses raw probabilities, independent of threshold.
        auc = roc_auc_score((y_true == dry_idx).astype(int), p_dry)
    except ValueError:
        auc = float('nan')
    cm = confusion_matrix(y_true, y_pred).tolist()
    return {
        'threshold': threshold,
        'acc': acc, 'precision_dry': p, 'recall_dry': r,
        'f1_dry': f, 'auc': auc, 'cm': cm,
    }


def sweep_thresholds(probs, y_true, dry_idx, lo=0.10, hi=0.90, step=0.01):
    """Returns list of metric dicts across thresholds."""
    out = []
    t = lo
    while t <= hi + 1e-9:
        out.append(metrics_at_threshold(probs, y_true, dry_idx, round(t, 3)))
        t += step
    return out


def pick_best(metrics_list, key):
    return max(metrics_list, key=lambda m: m[key])


def fmt(m):
    return (f"acc={m['acc']:.4f}  P={m['precision_dry']:.4f}  "
            f"R={m['recall_dry']:.4f}  F1={m['f1_dry']:.4f}  "
            f"AUC={m['auc']:.4f}  thr={m['threshold']:.2f}")


# ── Main ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='mps', choices=['mps', 'cuda', 'cpu'])
    ap.add_argument('--batch-size', type=int, default=16)
    ap.add_argument('--workers', type=int, default=0)
    args = ap.parse_args()

    if not os.path.isfile(WEIGHTS_PATH):
        raise SystemExit(f"✗ Weights not found: {WEIGHTS_PATH}")
    if not os.path.isdir(VAL_DIR) or not os.path.isdir(TEST_DIR):
        raise SystemExit(f"✗ Expected dataset under {DATASET_ROOT}/{{val,test}}")

    device = pick_device(args.device)
    print(f"🖥  Device: {device}\n")

    model, classes, img_size, mean, std, dry_idx = load_model(device)
    print(f"  val dir   : {VAL_DIR}")
    print(f"  test dir  : {TEST_DIR}\n")

    eval_tf  = base_eval_transform(img_size, mean, std)
    tta_list = tta_transforms(img_size, mean, std)

    # ── Step 1 — Baseline (no TTA, default threshold 0.5) ────────────
    print("══ Step 1 ══ Baseline (single forward, threshold 0.5)")
    test_ds = datasets.ImageFolder(TEST_DIR, transform=eval_tf)
    test_ld = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False,
                          num_workers=args.workers, pin_memory=False)
    # sanity: ImageFolder will sort alphabetically: ['dry','not_dry'].
    # dry_idx should match.
    assert test_ds.classes[dry_idx] == 'dry', \
        f"class order mismatch: {test_ds.classes}"

    probs_test_base, y_test = collect_probs(model, test_ld, device)
    base_metrics = metrics_at_threshold(probs_test_base, y_test, dry_idx, 0.5)
    print(f"  baseline: {fmt(base_metrics)}")
    print(f"  confusion (rows=true [dry,not_dry], cols=pred): {base_metrics['cm']}\n")

    # ── Step 2 — TTA on test set ─────────────────────────────────────
    print("══ Step 2 ══ TTA (5 augmented forward passes, averaged)")
    probs_test_tta, y_test_tta = collect_probs_tta(
        model, TEST_DIR, tta_list, args.batch_size, args.workers, device)
    assert np.array_equal(y_test, y_test_tta), "TTA target order mismatch"
    tta_metrics_default = metrics_at_threshold(
        probs_test_tta, y_test, dry_idx, 0.5)
    print(f"  tta@0.5  : {fmt(tta_metrics_default)}")
    print(f"  confusion: {tta_metrics_default['cm']}\n")

    # ── Step 3 — Threshold tuning on the VAL set (TTA) ───────────────
    print("══ Step 3 ══ Threshold tuning on VAL set (with TTA)")
    probs_val_tta, y_val = collect_probs_tta(
        model, VAL_DIR, tta_list, args.batch_size, args.workers, device)

    sweep = sweep_thresholds(probs_val_tta, y_val, dry_idx)
    best_f1  = pick_best(sweep, 'f1_dry')
    best_acc = pick_best(sweep, 'acc')
    print(f"  best-F1 on val : {fmt(best_f1)}")
    print(f"  best-acc on val: {fmt(best_acc)}\n")

    # Recommend the F1-optimal threshold (more meaningful for the
    # minority "dry" class than raw accuracy). Fall back to 0.5 if the
    # sweep produces nothing better than the default.
    chosen_thr = best_f1['threshold']
    print(f"➡  Chosen threshold (from val sweep, F1-optimal): {chosen_thr:.2f}")

    # ── Step 4 — Apply chosen threshold on the TEST set (TTA) ────────
    print("\n══ Step 4 ══ Final TEST-set metrics with TTA + tuned threshold")
    final = metrics_at_threshold(probs_test_tta, y_test, dry_idx, chosen_thr)
    print(f"  final    : {fmt(final)}")
    print(f"  confusion: {final['cm']}\n")

    # ── Step 5 — Summary table ───────────────────────────────────────
    print("══ Summary ══")
    print(f"{'':30}  {'acc':>7}  {'P_dry':>7}  {'R_dry':>7}  {'F1_dry':>7}  {'AUC':>7}")
    def row(label, m):
        print(f"  {label:28}  {m['acc']:.4f}  {m['precision_dry']:.4f}  "
              f"{m['recall_dry']:.4f}  {m['f1_dry']:.4f}  {m['auc']:.4f}")
    row("baseline (thr=0.5)",        base_metrics)
    row("TTA only (thr=0.5)",        tta_metrics_default)
    row(f"TTA + tuned (thr={chosen_thr:.2f})", final)

    # ── Step 6 — Persist calibration (NOT the .pth) ──────────────────
    calib = {
        'weights_file':           WEIGHTS_PATH,
        'classes':                classes,
        'dry_index':              int(dry_idx),
        'img_size':               int(img_size),
        'normalize_mean':         list(mean),
        'normalize_std':          list(std),
        'use_tta':                True,
        'tta_num_views':          len(tta_list),
        'tta_views':              ['original', 'hflip', 'rot+10', 'rot-10', 'brightness+0.15'],
        'decision_threshold':     float(chosen_thr),
        'threshold_selection':    'F1-optimal on val with TTA',
        'val_metrics_at_chosen':  best_f1,
        'test_metrics_at_chosen': final,
        'test_metrics_baseline':  base_metrics,
        'test_metrics_tta_only':  tta_metrics_default,
    }
    os.makedirs(os.path.dirname(CALIB_OUT), exist_ok=True)
    with open(CALIB_OUT, 'w') as f:
        json.dump(calib, f, indent=2)
    print(f"\n💾 Calibration written to: {CALIB_OUT}")
    print("   (dryness_v2.pth itself was NOT modified.)")


if __name__ == '__main__':
    main()
