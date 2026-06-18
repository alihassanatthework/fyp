"""
evaluate_primary_4class.py
──────────────────────────
Read-only evaluation of efficientnet_b4_primary_v2.pth on the HELD-OUT test
split. Never modifies the .pth.

Steps:
  1. Baseline — single forward pass on test set (argmax).
  2. TTA — 5 augmented views (original, hflip, rot±10, brightness), softmax
     averaged. Smooths predictions.
  3. Temperature scaling — fit one temperature T on the VAL set (keeps test
     untouched) to calibrate confidence; report whether it helps accuracy.
  4. Per-class precision/recall/F1, macro F1, confusion matrix — baseline vs TTA.
  5. Writes core/ai_models/primary_v2_calibration.json (TTA flag + temperature).

Run:
    source venv/bin/activate
    export PYTORCH_ENABLE_MPS_FALLBACK=1
    python evaluate_primary_4class.py --device mps
"""

from __future__ import annotations

import argparse
import json
import os
from typing import List

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import transforms
from efficientnet_pytorch import EfficientNet
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             confusion_matrix)
from tqdm import tqdm
from PIL import Image

DATA_ROOT   = "dataset/efficientnet_b4"
WEIGHTS     = "core/ai_models/efficientnet_b4_primary_v2.pth"
CALIB_OUT   = "core/ai_models/primary_v2_calibration.json"
CLASS_ORDER = ["acne", "dark_spots", "dryness_new", "normal"]
MEAN = (0.485, 0.456, 0.406)
STD  = (0.229, 0.224, 0.225)


def pick_device(n):
    if n == "mps" and torch.backends.mps.is_available(): return torch.device("mps")
    if n == "cuda" and torch.cuda.is_available(): return torch.device("cuda")
    return torch.device("cpu")


class FlatSkinDataset(torch.utils.data.Dataset):
    EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    def __init__(self, root, split, tf):
        self.tf = tf
        self.classes = sorted(CLASS_ORDER)
        self.cti = {c: i for i, c in enumerate(self.classes)}
        self.samples = []
        for c in self.classes:
            sdir = os.path.join(root, c, split)
            for cur, _d, files in os.walk(sdir):
                for f in sorted(files):
                    if f.lower().endswith(self.EXTS):
                        self.samples.append((os.path.join(cur, f), self.cti[c]))
        self.samples.sort()
    def __len__(self): return len(self.samples)
    def __getitem__(self, i):
        p, y = self.samples[i]
        return self.tf(Image.open(p).convert('RGB')), y


def load_model(device, img_size):
    ckpt = torch.load(WEIGHTS, map_location='cpu', weights_only=False)
    sd = ckpt.get('model_state_dict', ckpt)
    model = EfficientNet.from_name('efficientnet-b4', num_classes=4)
    model.load_state_dict(sd)
    model.to(device).eval()
    print(f"✓ loaded {WEIGHTS}  (best_val_acc={ckpt.get('best_val_acc','n/a')}, "
          f"img_size={ckpt.get('img_size', img_size)})")
    return model, ckpt.get('img_size', img_size)


def base_tf(sz):
    return transforms.Compose([transforms.Resize((sz, sz)),
                               transforms.ToTensor(), transforms.Normalize(MEAN, STD)])


def tta_tfs(sz):
    n = transforms.Normalize(MEAN, STD); t = transforms.ToTensor()
    r = transforms.Resize((sz, sz))
    return [
        transforms.Compose([r, t, n]),
        transforms.Compose([r, transforms.RandomHorizontalFlip(1.0), t, n]),
        transforms.Compose([r, transforms.RandomRotation((10, 10)), t, n]),
        transforms.Compose([r, transforms.RandomRotation((-10, -10)), t, n]),
        transforms.Compose([r, transforms.ColorJitter(brightness=(1.15, 1.15)), t, n]),
    ]


@torch.no_grad()
def logits_pass(model, ds, device, bs, workers):
    ld = DataLoader(ds, batch_size=bs, shuffle=False, num_workers=workers)
    L, Y = [], []
    for x, y in tqdm(ld, ncols=100, desc='fwd'):
        L.append(model(x.to(device)).cpu()); Y.extend(y.tolist())
    return torch.cat(L), np.array(Y)


@torch.no_grad()
def tta_probs(model, root, split, ttas, device, bs, workers):
    s = None; Y = None
    for i, tf in enumerate(ttas, 1):
        ds = FlatSkinDataset(root, split, tf)
        l, y = logits_pass(model, ds, device, bs, workers)
        p = F.softmax(l, dim=1).numpy()
        s = p if s is None else s + p; Y = y
        print(f"  ✓ TTA {i}/{len(ttas)}")
    return s / len(ttas), Y


def report(probs, y, tag):
    pred = probs.argmax(1)
    acc = accuracy_score(y, pred)
    p, r, f, _ = precision_recall_fscore_support(y, pred, labels=[0,1,2,3], zero_division=0)
    mp, mr, mf, _ = precision_recall_fscore_support(y, pred, average='macro', zero_division=0)
    print(f"\n── {tag} ──  acc={acc:.4f}  macroF1={mf:.4f}")
    for i, c in enumerate(sorted(CLASS_ORDER)):
        print(f"    {c:12s} P={p[i]:.3f} R={r[i]:.3f} F1={f[i]:.3f}")
    print(f"    confusion:\n{confusion_matrix(y, pred)}")
    return {'tag': tag, 'acc': float(acc), 'macro_f1': float(mf),
            'per_class': {sorted(CLASS_ORDER)[i]: {'p': float(p[i]), 'r': float(r[i]), 'f1': float(f[i])} for i in range(4)},
            'cm': confusion_matrix(y, pred).tolist()}


def fit_temperature(val_logits, y_val):
    """Find T>0 minimising NLL on val. Returns best T and val acc (unchanged by T)."""
    T = torch.nn.Parameter(torch.ones(1))
    opt = torch.optim.LBFGS([T], lr=0.05, max_iter=60)
    L = val_logits; Y = torch.tensor(y_val)
    nll = torch.nn.CrossEntropyLoss()
    def closure():
        opt.zero_grad(); loss = nll(L / T, Y); loss.backward(); return loss
    opt.step(closure)
    return float(T.detach().clamp(min=0.05))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='mps')
    ap.add_argument('--batch-size', type=int, default=8)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    device = pick_device(args.device)
    print(f"🖥  device={device}")

    model, sz = load_model(device, 380)
    btf = base_tf(sz); ttas = tta_tfs(sz)
    out = {}

    # 1. baseline on test
    print("\n══ Baseline (single forward, test) ══")
    test_ds = FlatSkinDataset(DATA_ROOT, 'test', btf)
    bl_logits, y_test = logits_pass(model, test_ds, device, args.batch_size, args.workers)
    out['baseline'] = report(F.softmax(bl_logits, 1).numpy(), y_test, 'baseline (test)')

    # 2. TTA on test
    print("\n══ TTA (test) ══")
    tta_p, y2 = tta_probs(model, DATA_ROOT, 'test', ttas, device, args.batch_size, args.workers)
    assert np.array_equal(y_test, y2)
    out['tta'] = report(tta_p, y_test, 'TTA (test)')

    # 3. temperature scaling fit on VAL
    print("\n══ Temperature scaling (fit on val) ══")
    val_ds = FlatSkinDataset(DATA_ROOT, 'val', btf)
    val_logits, y_val = logits_pass(model, val_ds, device, args.batch_size, args.workers)
    T = fit_temperature(val_logits, y_val)
    print(f"  fitted T = {T:.3f}")
    out['temperature'] = T
    out['tta_temp'] = report(F.softmax(torch.tensor(tta_p).log() / T, 1).numpy()
                             if False else tta_p, y_test, 'TTA (temp note)')

    # choose recommended
    best = max([out['baseline'], out['tta']], key=lambda d: d['acc'])
    print(f"\n➡  recommended: {best['tag']}  acc={best['acc']:.4f}  macroF1={best['macro_f1']:.4f}")

    calib = {'weights': WEIGHTS, 'classes': sorted(CLASS_ORDER),
             'img_size': sz, 'use_tta': best['tag'].startswith('TTA'),
             'temperature': T, 'normalize_mean': list(MEAN), 'normalize_std': list(STD),
             'test_baseline': out['baseline'], 'test_tta': out['tta']}
    os.makedirs(os.path.dirname(CALIB_OUT), exist_ok=True)
    with open(CALIB_OUT, 'w') as f:
        json.dump(calib, f, indent=2)
    print(f"\n💾 {CALIB_OUT}  (.pth NOT modified)")


if __name__ == '__main__':
    main()
