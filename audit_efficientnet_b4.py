"""
audit_efficientnet_b4.py
────────────────────────
READ-ONLY full audit of core/ai_models/efficientnet_b4_skin.pth across
all 4 classes (acne, dark_spots, dryness, normal).

Hard constraints honoured:
  • ONLY reads dataset/efficientnet_b4/train and dataset/efficientnet_b4/val.
  • Never touches dataset/efficientnet_b4/test or any other dataset folder.
  • Never modifies the .pth file or any data.
  • Writes its output ONLY to audit_efficientnet_b4_report/.

What it produces (under audit_efficientnet_b4_report/):
  1. metrics.json              — overall + per-class P/R/F1, accuracy
  2. confusion_matrix.png      — 4×4 raw + row-normalised
  3. confusion_matrix.json
  4. dataset_stats.json        — train/val class counts, imbalance ratios
  5. image_stats.json          — per-class per-split: brightness, contrast,
                                 mean RGB, mean HSV, resolution distribution
  6. leakage.json              — val images whose nearest train neighbour by
                                 perceptual hash is suspiciously close
                                 (Hamming distance ≤ leak_thresh)
  7. gradcam_<class>.png       — grid of worst-misclassified val samples per
                                 class with Grad-CAM overlay
  8. misclassified_<pair>.json — file lists of top confused (true→pred) pairs
  9. report.md                 — human-readable summary tying it all together

Usage:
    source venv/bin/activate
    python audit_efficientnet_b4.py --device mps

Optional flags:
    --val-limit       per-class cap for val evaluation (default: all)
    --stats-sample    per-class images for image-stat sampling (default: 200)
    --leak-train-sample per-class train images hashed for leakage (default: 400)
    --leak-thresh     pHash Hamming dist ≤ this counts as "near-duplicate" (default: 6)
    --gradcam-k       worst misclassifications per class for Grad-CAM (default: 12)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from efficientnet_pytorch import EfficientNet
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, confusion_matrix,
)
from tqdm import tqdm


# ── Constants ───────────────────────────────────────────────────────
SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)

CLASSES   = ['acne', 'dark_spots', 'dryness', 'normal']  # alphabetical
IMG_SIZE  = 380   # native EfficientNet-B4 input used at training time
MEAN      = (0.485, 0.456, 0.406)
STD       = (0.229, 0.224, 0.225)

DATASET_ROOT  = "dataset/efficientnet_b4"
TRAIN_DIR     = f"{DATASET_ROOT}/train"
VAL_DIR       = f"{DATASET_ROOT}/val"
WEIGHTS_PATH  = "core/ai_models/efficientnet_b4_skin.pth"
OUT_DIR       = "audit_efficientnet_b4_report"

# Safety: anything outside train/val under DATASET_ROOT is OFF-LIMITS.
ALLOWED_DATA_PATHS = (TRAIN_DIR, VAL_DIR)


# ── Device ──────────────────────────────────────────────────────────
def pick_device(name: str) -> torch.device:
    if name == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    if name == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# ── Model ───────────────────────────────────────────────────────────
def load_model(device):
    model = EfficientNet.from_name('efficientnet-b4', num_classes=len(CLASSES))
    sd = torch.load(WEIGHTS_PATH, map_location='cpu', weights_only=False)
    if isinstance(sd, dict) and 'state_dict' in sd:
        sd = sd['state_dict']
    if isinstance(sd, dict) and 'model_state_dict' in sd:
        sd = sd['model_state_dict']
    missing, unexpected = model.load_state_dict(sd, strict=False)
    print(f"✓ Loaded {WEIGHTS_PATH}")
    print(f"  missing keys:    {len(missing)}")
    print(f"  unexpected keys: {len(unexpected)}")
    model.to(device).eval()
    return model


# ── Dataset (custom: keeps file path for reporting) ─────────────────
class LabeledFolderDS(Dataset):
    """Returns (tensor, label, path). Restricted to ALLOWED_DATA_PATHS."""
    def __init__(self, root: str, transform, per_class_limit=None):
        if root not in ALLOWED_DATA_PATHS:
            raise RuntimeError(f"Refusing to read disallowed path: {root}")
        self.tf = transform
        self.items: List[Tuple[str, int]] = []
        for ci, cls in enumerate(CLASSES):
            cls_dir = os.path.join(root, cls)
            if not os.path.isdir(cls_dir):
                continue
            files = sorted(os.listdir(cls_dir))
            files = [f for f in files
                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]
            if per_class_limit:
                random.Random(SEED + ci).shuffle(files)
                files = files[:per_class_limit]
            for f in files:
                self.items.append((os.path.join(cls_dir, f), ci))
        # deterministic order for reproducibility
        self.items.sort(key=lambda t: t[0])

    def __len__(self): return len(self.items)

    def __getitem__(self, i):
        path, label = self.items[i]
        img = Image.open(path).convert('RGB')
        return self.tf(img), label, path


def eval_transform():
    return transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


# ── Section 1: per-class metrics + confusion matrix on val ──────────
@torch.no_grad()
def evaluate_val(model, device, val_limit, batch_size, workers):
    print("\n══ Section 1 ══ Val evaluation + confusion matrix")
    ds = LabeledFolderDS(VAL_DIR, eval_transform(), per_class_limit=val_limit)
    print(f"  val samples used: {len(ds)} (per_class_limit={val_limit})")
    ld = DataLoader(ds, batch_size=batch_size, shuffle=False,
                     num_workers=workers, pin_memory=False)

    y_true, y_pred, y_prob, paths = [], [], [], []
    for imgs, labels, ps in tqdm(ld, ncols=100, desc='val'):
        imgs = imgs.to(device)
        logits = model(imgs)
        probs = F.softmax(logits, dim=1).cpu().numpy()
        preds = probs.argmax(1)
        y_true.extend(labels.numpy().tolist())
        y_pred.extend(preds.tolist())
        y_prob.extend(probs.tolist())
        paths.extend(ps)

    y_true = np.array(y_true); y_pred = np.array(y_pred)
    y_prob = np.array(y_prob)
    overall_acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(CLASSES))))
    p, r, f1, sup = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(len(CLASSES))), zero_division=0)
    pmac, rmac, fmac, _ = precision_recall_fscore_support(
        y_true, y_pred, average='macro', zero_division=0)

    per_class = {}
    for i, c in enumerate(CLASSES):
        per_class[c] = {
            'support':   int(sup[i]),
            'precision': float(p[i]),
            'recall':    float(r[i]),
            'f1':        float(f1[i]),
            'accuracy':  float((y_pred[y_true == i] == i).mean()) if (y_true == i).any() else 0.0,
        }

    metrics = {
        'overall_accuracy': float(overall_acc),
        'macro_precision':  float(pmac),
        'macro_recall':     float(rmac),
        'macro_f1':         float(fmac),
        'per_class':        per_class,
    }
    print(f"  overall acc: {overall_acc:.4f}   macro F1: {fmac:.4f}")
    for c in CLASSES:
        pc = per_class[c]
        print(f"    {c:11s}  acc={pc['accuracy']:.3f}  P={pc['precision']:.3f}"
              f"  R={pc['recall']:.3f}  F1={pc['f1']:.3f}  n={pc['support']}")

    # confusion matrix figure
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    for ax, mat, title in [
        (axes[0], cm, 'Confusion matrix (counts)'),
        (axes[1], cm / np.maximum(cm.sum(axis=1, keepdims=True), 1),
                 'Confusion matrix (row-normalised)'),
    ]:
        im = ax.imshow(mat, cmap='Blues')
        ax.set_xticks(range(4)); ax.set_yticks(range(4))
        ax.set_xticklabels(CLASSES, rotation=30, ha='right')
        ax.set_yticklabels(CLASSES)
        ax.set_xlabel('Predicted'); ax.set_ylabel('True')
        ax.set_title(title)
        for i in range(4):
            for j in range(4):
                v = mat[i, j]
                ax.text(j, i, f'{v:.2f}' if mat.dtype != np.int64 else str(int(v)),
                         ha='center', va='center',
                         color='white' if v > mat.max()/2 else 'black', fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle(f'Validation confusion — overall acc {overall_acc:.3f}, macro F1 {fmac:.3f}')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'confusion_matrix.png'), dpi=140)
    plt.close(fig)

    with open(os.path.join(OUT_DIR, 'confusion_matrix.json'), 'w') as f:
        json.dump({'classes': CLASSES, 'matrix_counts': cm.tolist()}, f, indent=2)
    with open(os.path.join(OUT_DIR, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)

    return y_true, y_pred, y_prob, paths, cm, metrics


# ── Section 2: dataset stats + class distribution ───────────────────
def count_files(root):
    counts = {}
    for c in CLASSES:
        p = os.path.join(root, c)
        if os.path.isdir(p):
            counts[c] = sum(1 for f in os.listdir(p)
                              if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')))
        else:
            counts[c] = 0
    return counts


def dataset_stats():
    print("\n══ Section 2 ══ Dataset distribution (train + val)")
    train_counts = count_files(TRAIN_DIR)
    val_counts   = count_files(VAL_DIR)

    def imbalance(d):
        vals = list(d.values())
        return float(max(vals) / max(1, min(vals)))

    stats = {
        'train_counts':         train_counts,
        'val_counts':           val_counts,
        'train_total':          sum(train_counts.values()),
        'val_total':            sum(val_counts.values()),
        'train_imbalance_ratio': imbalance(train_counts),
        'val_imbalance_ratio':   imbalance(val_counts),
        'train_pct': {k: round(v / max(1, sum(train_counts.values())) * 100, 2)
                       for k, v in train_counts.items()},
        'val_pct':   {k: round(v / max(1, sum(val_counts.values())) * 100, 2)
                       for k, v in val_counts.items()},
    }
    print(f"  train total: {stats['train_total']}  imbalance: {stats['train_imbalance_ratio']:.2f}x")
    print(f"  val   total: {stats['val_total']}  imbalance: {stats['val_imbalance_ratio']:.2f}x")
    for c in CLASSES:
        print(f"    {c:11s}  train={train_counts[c]:>5}  ({stats['train_pct'][c]:>5.2f}%)"
              f"   val={val_counts[c]:>5}  ({stats['val_pct'][c]:>5.2f}%)")
    with open(os.path.join(OUT_DIR, 'dataset_stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)
    return stats


# ── Section 3: image-level stats per class per split ────────────────
def image_stats_for_files(files: List[str]) -> dict:
    """Aggregate brightness / contrast / mean RGB / HSV / resolution."""
    brightness, contrast = [], []
    rgb_mean, hsv_mean   = [], []
    widths, heights      = [], []
    for fp in files:
        try:
            img = cv2.imread(fp)
            if img is None:
                continue
            h, w = img.shape[:2]
            widths.append(w); heights.append(h)
            # downsize for speed
            small = cv2.resize(img, (128, 128))
            rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            hsv   = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            brightness.append(float(gray.mean()))
            contrast.append(float(gray.std()))
            rgb_mean.append(rgb.mean(axis=(0, 1)).tolist())
            hsv_mean.append(hsv.mean(axis=(0, 1)).tolist())
        except Exception:
            continue

    if not brightness:
        return {'n': 0}
    rgb_arr = np.array(rgb_mean)
    hsv_arr = np.array(hsv_mean)
    return {
        'n':           len(brightness),
        'brightness':  {'mean': float(np.mean(brightness)), 'std': float(np.std(brightness))},
        'contrast':    {'mean': float(np.mean(contrast)),   'std': float(np.std(contrast))},
        'rgb_mean':    {'R': float(rgb_arr[:, 0].mean()),
                         'G': float(rgb_arr[:, 1].mean()),
                         'B': float(rgb_arr[:, 2].mean())},
        'hsv_mean':    {'H': float(hsv_arr[:, 0].mean()),
                         'S': float(hsv_arr[:, 1].mean()),
                         'V': float(hsv_arr[:, 2].mean())},
        'resolution':  {'width_mean':  float(np.mean(widths)),
                         'height_mean': float(np.mean(heights)),
                         'width_std':   float(np.std(widths)),
                         'height_std':  float(np.std(heights))},
    }


def list_class_files(root, cls, limit, salt=0):
    cls_dir = os.path.join(root, cls)
    files = [os.path.join(cls_dir, f) for f in sorted(os.listdir(cls_dir))
             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]
    rng = random.Random(SEED + salt)
    rng.shuffle(files)
    return files[:limit] if limit else files


def image_stats_section(stats_sample):
    print(f"\n══ Section 3 ══ Image stats per class (sample={stats_sample}/class/split)")
    out = {'sample_per_class': stats_sample, 'classes': {}}
    for cls in CLASSES:
        out['classes'][cls] = {}
        for split, root in [('train', TRAIN_DIR), ('val', VAL_DIR)]:
            files = list_class_files(root, cls, stats_sample, salt=hash(split) & 0xff)
            s = image_stats_for_files(files)
            out['classes'][cls][split] = s
            if s.get('n'):
                print(f"  {cls:11s} {split:5s}  n={s['n']}  "
                      f"bright={s['brightness']['mean']:.1f}±{s['brightness']['std']:.1f}  "
                      f"contrast={s['contrast']['mean']:.1f}  "
                      f"res={s['resolution']['width_mean']:.0f}x{s['resolution']['height_mean']:.0f}")
    with open(os.path.join(OUT_DIR, 'image_stats.json'), 'w') as f:
        json.dump(out, f, indent=2)

    # Train-vs-val drift figure: brightness + contrast per class
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    width = 0.35; x = np.arange(len(CLASSES))
    for ax, key, ylabel in [(axes[0], 'brightness', 'Brightness (0–255)'),
                              (axes[1], 'contrast',   'Contrast (std of gray)')]:
        tr = [out['classes'][c]['train'].get(key, {}).get('mean', 0) for c in CLASSES]
        va = [out['classes'][c]['val'].get(key, {}).get('mean', 0) for c in CLASSES]
        ax.bar(x - width/2, tr, width, label='train')
        ax.bar(x + width/2, va, width, label='val')
        ax.set_xticks(x); ax.set_xticklabels(CLASSES, rotation=20)
        ax.set_ylabel(ylabel); ax.set_title(f'{key} — train vs val')
        ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'train_vs_val_drift.png'), dpi=140)
    plt.close(fig)
    return out


# ── Section 4: Leakage check via perceptual hash ────────────────────
def phash(image_bgr) -> np.ndarray:
    """64-bit perceptual hash via 8×8 DCT (median trick)."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    g32  = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct  = cv2.dct(g32)
    low  = dct[:8, :8]
    med  = np.median(low[1:])  # exclude DC term
    bits = (low > med).flatten().astype(np.uint8)
    return bits  # 64-bit vector


def hamming(a, b):
    return int(np.count_nonzero(a != b))


def hash_files(files):
    out = []
    for fp in files:
        img = cv2.imread(fp)
        if img is None:
            continue
        out.append((fp, phash(img)))
    return out


def leakage_section(leak_train_sample, leak_thresh):
    print(f"\n══ Section 4 ══ Leakage check (pHash, train_sample={leak_train_sample}/class, thresh≤{leak_thresh})")
    leakage = {'threshold_hamming': leak_thresh, 'per_class': {}, 'total_near_duplicates': 0}

    for cls in CLASSES:
        # Subsample train and val for tractability.
        train_files = list_class_files(TRAIN_DIR, cls, leak_train_sample, salt=1)
        val_files   = list_class_files(VAL_DIR,   cls, 300,                salt=2)
        print(f"  {cls}: hashing train={len(train_files)}  val={len(val_files)}")

        train_h = hash_files(train_files)
        val_h   = hash_files(val_files)
        train_mat = np.array([h for _, h in train_h]) if train_h else np.zeros((0, 64))

        suspects = []
        for vp, vh in val_h:
            if train_mat.size == 0:
                break
            dists = np.count_nonzero(train_mat != vh, axis=1)
            j = int(dists.argmin())
            d = int(dists[j])
            if d <= leak_thresh:
                suspects.append({
                    'val_file':            vp,
                    'nearest_train_file':  train_h[j][0],
                    'hamming_distance':    d,
                })
        suspects.sort(key=lambda s: s['hamming_distance'])
        leakage['per_class'][cls] = {
            'val_hashed':           len(val_h),
            'train_hashed':         len(train_h),
            'near_duplicate_count': len(suspects),
            'near_duplicate_pct':   round(100 * len(suspects) / max(1, len(val_h)), 2),
            'examples':             suspects[:20],
        }
        leakage['total_near_duplicates'] += len(suspects)
        print(f"    near-duplicate val→train: {len(suspects)}/{len(val_h)} "
              f"({leakage['per_class'][cls]['near_duplicate_pct']}%)")

    with open(os.path.join(OUT_DIR, 'leakage.json'), 'w') as f:
        json.dump(leakage, f, indent=2)
    return leakage


# ── Section 5: Grad-CAM on top-K misclassifications per class ───────
class GradCAM:
    """Grad-CAM hooked on EfficientNet-pytorch's `_conv_head` (final conv)."""
    def __init__(self, model):
        self.model = model
        self.activations = None
        self.gradients   = None
        target = model._conv_head
        target.register_forward_hook(self._fwd)
        target.register_full_backward_hook(self._bwd)

    def _fwd(self, m, i, o): self.activations = o.detach()
    def _bwd(self, m, gi, go): self.gradients = go[0].detach()

    def __call__(self, x, class_idx):
        self.model.zero_grad(set_to_none=True)
        logits = self.model(x)
        score  = logits[0, class_idx]
        score.backward(retain_graph=False)
        # global-average-pool gradients → weights
        w = self.gradients.mean(dim=(2, 3), keepdim=True)         # (1,C,1,1)
        cam = (w * self.activations).sum(dim=1, keepdim=True)     # (1,1,H,W)
        cam = F.relu(cam)
        cam = F.interpolate(cam, size=(IMG_SIZE, IMG_SIZE),
                             mode='bilinear', align_corners=False)
        cam = cam.squeeze().cpu().numpy()
        if cam.max() > 0:
            cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-9)
        return cam, F.softmax(logits, dim=1).detach().cpu().numpy()[0]


def overlay_cam(rgb_img, cam):
    heat = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    out  = (0.55 * rgb_img + 0.45 * heat).clip(0, 255).astype(np.uint8)
    return out


def gradcam_section(model, device, y_true, y_pred, y_prob, paths, k):
    print(f"\n══ Section 5 ══ Grad-CAM on top-{k} worst misclassifications per class")
    cam_fn = GradCAM(model)
    tf = eval_transform()
    misc_pairs = defaultdict(list)  # (true, pred) → list

    # Find top-K worst-misclassified samples per true class
    # "worst" = highest probability assigned to wrong class.
    for i, (yt, yp, prob, pth) in enumerate(zip(y_true, y_pred, y_prob, paths)):
        if yt != yp:
            misc_pairs[(int(yt), int(yp))].append((float(prob[yp]), pth, prob.tolist()))

    # Save pair-by-pair file lists
    pair_dump = {}
    for (yt, yp), lst in misc_pairs.items():
        lst.sort(key=lambda x: -x[0])  # most confident wrong first
        key = f"{CLASSES[yt]}->{CLASSES[yp]}"
        pair_dump[key] = {
            'count':    len(lst),
            'examples': [{'file': p, 'wrong_class_prob': c, 'all_probs': pr}
                         for c, p, pr in lst[:25]],
        }
    with open(os.path.join(OUT_DIR, 'misclassified_pairs.json'), 'w') as f:
        json.dump(pair_dump, f, indent=2)

    # Per-true-class Grad-CAM grids
    for ci, cls in enumerate(CLASSES):
        # gather worst-K across all wrong predictions for this true class
        bucket = []
        for (yt, yp), lst in misc_pairs.items():
            if yt == ci:
                bucket.extend([(c, p, yp, pr) for c, p, pr in lst])
        bucket.sort(key=lambda x: -x[0])
        bucket = bucket[:k]
        if not bucket:
            print(f"  {cls}: no misclassifications — skipping")
            continue

        cols = 4
        rows = math.ceil(len(bucket) / cols)
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.4, rows * 3.6))
        if rows == 1:
            axes = np.array([axes])
        for ax in axes.flat:
            ax.axis('off')

        for idx, (wprob, pth, ypred, probs) in enumerate(bucket):
            try:
                pil = Image.open(pth).convert('RGB').resize((IMG_SIZE, IMG_SIZE))
                rgb = np.array(pil)
                x = tf(Image.open(pth).convert('RGB')).unsqueeze(0).to(device)
                cam, _ = cam_fn(x, ci)  # CAM w.r.t. the TRUE class
                vis = overlay_cam(rgb, cam)
                ax = axes.flat[idx]
                ax.imshow(vis)
                base = os.path.basename(pth)
                ax.set_title(
                    f"true={cls}\npred={CLASSES[ypred]} ({wprob:.2f})\n{base[:28]}",
                    fontsize=8)
            except Exception as e:
                print(f"  ! gradcam failed on {pth}: {e}")
        fig.suptitle(f"Grad-CAM (vs TRUE class={cls}) — worst {len(bucket)} misclassifications",
                      fontsize=12)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, f'gradcam_{cls}.png'), dpi=130)
        plt.close(fig)
        print(f"  ✓ gradcam_{cls}.png ({len(bucket)} samples)")

    return pair_dump


# ── Section 6: Root-cause hypotheses + recommendations ──────────────
def synthesize_report(metrics, ds_stats, img_stats, leakage, pair_dump):
    """Write report.md tying everything together with concrete recommendations."""
    lines = []
    lines.append("# EfficientNet-B4 (4-class) — Read-Only Audit Report\n")
    lines.append(f"Weights: `{WEIGHTS_PATH}`  ·  Data (read-only): "
                  f"`{TRAIN_DIR}`, `{VAL_DIR}`\n")
    lines.append("> This audit modified NOTHING — model and data are untouched.\n")

    # ── Overall ────────────────────────────────────────────────────
    lines.append("## 1. Overall validation performance\n")
    lines.append(f"- **Overall accuracy:** {metrics['overall_accuracy']:.4f}")
    lines.append(f"- **Macro F1:** {metrics['macro_f1']:.4f}")
    lines.append(f"- **Macro precision:** {metrics['macro_precision']:.4f}")
    lines.append(f"- **Macro recall:** {metrics['macro_recall']:.4f}\n")
    lines.append("| Class | Acc | Precision | Recall | F1 | Support |")
    lines.append("|---|---|---|---|---|---|")
    for c in CLASSES:
        pc = metrics['per_class'][c]
        lines.append(f"| {c} | {pc['accuracy']:.3f} | {pc['precision']:.3f} | "
                      f"{pc['recall']:.3f} | {pc['f1']:.3f} | {pc['support']} |")
    lines.append("\nSee `confusion_matrix.png` for the full 4×4 confusion grid.\n")

    # ── Class distribution ─────────────────────────────────────────
    lines.append("## 2. Dataset distribution (train + val only)\n")
    lines.append(f"- Train total: **{ds_stats['train_total']}** · "
                  f"imbalance **{ds_stats['train_imbalance_ratio']:.2f}×**")
    lines.append(f"- Val total:   **{ds_stats['val_total']}** · "
                  f"imbalance **{ds_stats['val_imbalance_ratio']:.2f}×**\n")
    lines.append("| Class | train | train % | val | val % |")
    lines.append("|---|---|---|---|---|")
    for c in CLASSES:
        lines.append(f"| {c} | {ds_stats['train_counts'][c]} | "
                      f"{ds_stats['train_pct'][c]}% | "
                      f"{ds_stats['val_counts'][c]} | "
                      f"{ds_stats['val_pct'][c]}% |")
    lines.append("")

    # Imbalance flag
    if ds_stats['train_imbalance_ratio'] > 4:
        lines.append(f"⚠ **Train imbalance is {ds_stats['train_imbalance_ratio']:.1f}×** — "
                      "minority classes are likely under-fitted. The model can score high "
                      "overall accuracy by leaning toward the majority class "
                      f"(`{max(ds_stats['train_counts'], key=ds_stats['train_counts'].get)}`).\n")
    if abs(ds_stats['val_imbalance_ratio'] - ds_stats['train_imbalance_ratio']) > 2:
        lines.append("⚠ **Train and val have very different class proportions** — "
                      "val accuracy is *not* directly comparable to real-world deployment.\n")

    # ── Train/Val drift ────────────────────────────────────────────
    lines.append("## 3. Train vs Val image-statistic drift\n")
    lines.append(f"Sample size per class per split: **{img_stats['sample_per_class']}**\n")
    lines.append("| Class | split | brightness | contrast | mean R/G/B | mean H/S/V | res |")
    lines.append("|---|---|---|---|---|---|---|")
    for c in CLASSES:
        for split in ['train', 'val']:
            s = img_stats['classes'][c][split]
            if not s.get('n'): continue
            rgb = s['rgb_mean']; hsv = s['hsv_mean']; res = s['resolution']
            lines.append(f"| {c} | {split} | "
                          f"{s['brightness']['mean']:.1f}±{s['brightness']['std']:.1f} | "
                          f"{s['contrast']['mean']:.1f} | "
                          f"{rgb['R']:.0f}/{rgb['G']:.0f}/{rgb['B']:.0f} | "
                          f"{hsv['H']:.0f}/{hsv['S']:.0f}/{hsv['V']:.0f} | "
                          f"{res['width_mean']:.0f}×{res['height_mean']:.0f} |")
    lines.append("")
    drift_flags = []
    for c in CLASSES:
        tr = img_stats['classes'][c].get('train', {})
        va = img_stats['classes'][c].get('val', {})
        if tr.get('n') and va.get('n'):
            db = abs(tr['brightness']['mean'] - va['brightness']['mean'])
            dc = abs(tr['contrast']['mean'] - va['contrast']['mean'])
            if db > 20 or dc > 12:
                drift_flags.append(
                    f"- **{c}**: brightness Δ={db:.1f}, contrast Δ={dc:.1f}")
    if drift_flags:
        lines.append("⚠ **Train-val distribution drift detected** "
                      "(visible in `train_vs_val_drift.png`):")
        lines.extend(drift_flags)
        lines.append("\nThis means high val accuracy is partly **overfitting "
                      "to dataset artefacts** (lighting, camera, background) "
                      "rather than to true skin condition signals — which "
                      "directly explains why open-source / phone images "
                      "perform much worse than val.\n")

    # ── Leakage ────────────────────────────────────────────────────
    lines.append("## 4. Train↔Val leakage (perceptual hash)\n")
    lines.append(f"Threshold: Hamming distance ≤ **{leakage['threshold_hamming']}** "
                  "on 64-bit DCT pHash.\n")
    lines.append("| Class | val hashed | near-dup count | near-dup % |")
    lines.append("|---|---|---|---|")
    severe = []
    for c in CLASSES:
        info = leakage['per_class'][c]
        lines.append(f"| {c} | {info['val_hashed']} | "
                      f"{info['near_duplicate_count']} | "
                      f"{info['near_duplicate_pct']}% |")
        if info['near_duplicate_pct'] >= 5:
            severe.append((c, info['near_duplicate_pct']))
    lines.append("")
    if severe:
        lines.append("⚠ **Leakage suspected** — val images are very similar "
                      "to train images for: " +
                      ", ".join(f"`{c}` ({pct}%)" for c, pct in severe) +
                      ". When val is contaminated by train look-alikes, the "
                      "reported val accuracy is **inflated** and the model "
                      "memorises the dataset rather than learning the condition. "
                      "Example file pairs are in `leakage.json`.\n")
    else:
        lines.append("✓ No widespread near-duplicate leakage detected.\n")

    # ── Confusion pairs ───────────────────────────────────────────
    lines.append("## 5. Top confused class pairs\n")
    flat = [(k, v['count']) for k, v in pair_dump.items()]
    flat.sort(key=lambda x: -x[1])
    if flat:
        lines.append("| (true → predicted) | count |")
        lines.append("|---|---|")
        for k, n in flat[:12]:
            lines.append(f"| {k} | {n} |")
    lines.append("\nGrad-CAM grids per true class are in "
                  "`gradcam_<class>.png` — these show **what the model is "
                  "actually looking at** when it makes mistakes. Use them to "
                  "verify whether the model focuses on real skin features "
                  "(pores, pigmentation, texture) or on irrelevant cues "
                  "(background, hair, lighting, watermarks).\n")

    # ── Root causes + recommendations per class ────────────────────
    lines.append("## 6. Per-class root-cause hypotheses & recommended fixes\n")
    for c in CLASSES:
        pc = metrics['per_class'][c]
        lines.append(f"### {c}\n")
        lines.append(f"- Val accuracy: **{pc['accuracy']:.3f}**  · F1: "
                      f"**{pc['f1']:.3f}** · support: {pc['support']}")

        # weakness diagnostics
        diag = []
        # 1. severe imbalance
        share = ds_stats['train_pct'][c]
        if share < 10:
            diag.append(f"Under-represented in training ({share}%) — the model "
                          f"sees `{c}` rarely vs the majority class.")
        elif share > 50:
            diag.append(f"Over-represented in training ({share}%) — the model "
                          "may default to this class on ambiguous inputs.")

        # 2. low recall but high precision = under-prediction
        if pc['precision'] > pc['recall'] + 0.15:
            diag.append("High precision, low recall → model is **too "
                          "conservative**: when it says " + c + ", it's usually "
                          "right, but it misses many real cases.")
        # 3. low precision but high recall = over-prediction
        if pc['recall'] > pc['precision'] + 0.15:
            diag.append("High recall, low precision → model **over-predicts** "
                          + c + " — many false positives from other classes.")
        # 4. drift
        tr = img_stats['classes'][c].get('train', {})
        va = img_stats['classes'][c].get('val', {})
        if tr.get('n') and va.get('n'):
            db = abs(tr['brightness']['mean'] - va['brightness']['mean'])
            if db > 20:
                diag.append(f"Visual drift train↔val (Δbrightness {db:.1f}) — "
                              "validation lighting differs from training, "
                              "model may rely on lighting cues.")
        # 5. leakage
        leak_pct = leakage['per_class'][c]['near_duplicate_pct']
        if leak_pct >= 5:
            diag.append(f"~{leak_pct}% of val samples look almost identical "
                          "to train — val accuracy here is partly memorisation.")

        # 6. top confusion partners
        partners = [(k, v['count']) for k, v in pair_dump.items() if k.startswith(c + '->')]
        partners.sort(key=lambda x: -x[1])
        if partners:
            top = ', '.join(f"{k.split('->')[1]} ({n})" for k, n in partners[:3])
            diag.append(f"Most often confused with: **{top}** — see Grad-CAM "
                          f"to check whether the model is looking at the right "
                          f"region for these failures.")
        if not diag:
            diag.append("No major structural weakness detected from these signals.")

        for d in diag:
            lines.append(f"- {d}")

        # recommendations
        recs = []
        if share < 10:
            recs.append("Add more training data OR use class-weighted loss "
                          "/ WeightedRandomSampler.")
        if pc['f1'] < 0.6:
            recs.append("Consider training a **dedicated binary specialist** "
                          f"for `{c}` (same recipe used for `dryness_v2.pth`) "
                          "and use Pattern-1 specialist override at inference.")
        if leak_pct >= 5:
            recs.append("De-duplicate train↔val using pHash before trusting any "
                          "future re-training metrics.")
        if tr.get('n') and va.get('n') and abs(
                tr['brightness']['mean'] - va['brightness']['mean']) > 20:
            recs.append("Strengthen augmentation: ColorJitter (brightness, "
                          "contrast, saturation), RandAugment, GaussianBlur. "
                          "This forces the model to use texture, not lighting.")
        if partners:
            top_pair = partners[0][0]
            recs.append(f"For the most common confusion ({top_pair}), inspect "
                          "Grad-CAM grid: if the model attends to background "
                          "/ hair, crop tighter to facial ROI before classification.")
        if not recs:
            recs.append("Current performance is acceptable; defer changes until "
                          "other classes are addressed.")
        lines.append("\n**Recommended fixes:**")
        for r in recs:
            lines.append(f"- {r}")
        lines.append("")

    # ── Strategic summary ──────────────────────────────────────────
    lines.append("## 7. Strategic summary\n")
    sorted_classes = sorted(CLASSES, key=lambda c: metrics['per_class'][c]['f1'])
    weakest = sorted_classes[0]
    strongest = sorted_classes[-1]
    lines.append(f"- Weakest class: **{weakest}** "
                  f"(F1 {metrics['per_class'][weakest]['f1']:.3f})")
    lines.append(f"- Strongest class: **{strongest}** "
                  f"(F1 {metrics['per_class'][strongest]['f1']:.3f})")
    lines.append("- The gap between weakest and strongest tells you whether to "
                  "(a) build a single new general model, or (b) train one or two "
                  "specialists (like `dryness_v2.pth`) and use specialist-override "
                  "at inference. Specialists win when one class is dramatically "
                  "worse than the others.\n")
    lines.append("> Next decision is yours — this report is read-only. "
                  "Reply with which class(es) you want to address first.\n")

    out_path = os.path.join(OUT_DIR, 'report.md')
    with open(out_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"\n📝 Report written: {out_path}")


# ── Main ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='mps', choices=['mps', 'cuda', 'cpu'])
    ap.add_argument('--batch-size', type=int, default=16)
    ap.add_argument('--workers', type=int, default=0)
    ap.add_argument('--val-limit', type=int, default=None,
                    help='Per-class cap for val eval (default: use all).')
    ap.add_argument('--stats-sample', type=int, default=200,
                    help='Per-class images for image-stat computation.')
    ap.add_argument('--leak-train-sample', type=int, default=400,
                    help='Per-class train images hashed for leakage check.')
    ap.add_argument('--leak-thresh', type=int, default=6,
                    help='pHash Hamming distance ≤ this counts as near-duplicate.')
    ap.add_argument('--gradcam-k', type=int, default=12,
                    help='Worst-N misclassifications per true class for Grad-CAM.')
    args = ap.parse_args()

    if not os.path.isfile(WEIGHTS_PATH):
        raise SystemExit(f"✗ Weights not found: {WEIGHTS_PATH}")
    for p in ALLOWED_DATA_PATHS:
        if not os.path.isdir(p):
            raise SystemExit(f"✗ Required folder missing: {p}")

    os.makedirs(OUT_DIR, exist_ok=True)
    device = pick_device(args.device)
    print(f"🖥  Device: {device}")
    print(f"📂 Output : {OUT_DIR}/")
    t0 = time.time()

    model = load_model(device)

    y_true, y_pred, y_prob, paths, cm, metrics = evaluate_val(
        model, device, args.val_limit, args.batch_size, args.workers)
    ds_stats   = dataset_stats()
    img_stats  = image_stats_section(args.stats_sample)
    leakage    = leakage_section(args.leak_train_sample, args.leak_thresh)
    pair_dump  = gradcam_section(model, device, y_true, y_pred, y_prob,
                                   paths, args.gradcam_k)
    synthesize_report(metrics, ds_stats, img_stats, leakage, pair_dump)

    elapsed = time.time() - t0
    print(f"\n✅ Audit complete in {elapsed/60:.1f} min.")
    print(f"   See: {OUT_DIR}/report.md")
    print(f"   No files outside {OUT_DIR}/ were created or modified.")


if __name__ == '__main__':
    main()
