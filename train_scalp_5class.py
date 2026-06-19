"""
train_scalp_5class.py
─────────────────────
Phase 2 — train the 5-class SCALP classifier on dataset/scalp_clean/.

Classes (ImageFolder alphabetical → fixed index order):
    0 Alopecia   1 Dermatitis   2 Infections   3 Normal   4 Psoriasis

Architecture: EfficientNet-B0 (efficientnet_pytorch), 224×224, 5-class _fc head.
B0 (not B4) on purpose — ~9.7k images trains fast on MPS and resists overfitting.
Output checkpoint is loaded by core/ai_models/scalp_classifier.py.

Recipe (mirrors train_primary_4class.py):
  • Phase 1: _fc head only, 4 epochs, lr 1e-3.
  • Phase 2: full unfreeze, lr 1e-4, cosine + warmup, up to 40 epochs.
  • Imbalance (~3×): WeightedRandomSampler (augmentation is RUNTIME-only — no
    disk-baked copies, so no leakage).
  • Loss: CrossEntropy label_smoothing 0.1 + MixUp α=0.2 (Phase 2).
  • Augment: RandAugment + flip + rotation + color jitter + blur.
  • AMP OFF by default (float16 autocast is unstable for EfficientNet on MPS).
  • Early stop: patience 7 on val accuracy. Incremental best-save (crash-safe).

Outputs (never overwrites an existing .pth):
  • core/ai_models/scalp_classifier_v1.pth
  • training_log_scalp_v1.json

Run via scripts/train_scalp.sh (recommended), or:
  python train_scalp_5class.py --device mps          # full run
  python train_scalp_5class.py --limit 200 --phase2-epochs 1   # smoke test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler, Subset
from torchvision import datasets, transforms
from efficientnet_pytorch import EfficientNet
from sklearn.metrics import (precision_recall_fscore_support, accuracy_score,
                             confusion_matrix)
from tqdm import tqdm

DATA_ROOT   = "dataset/scalp_clean"
OUT_WEIGHTS = "core/ai_models/scalp_classifier_v1.pth"
OUT_LOG     = "training_log_scalp_v1.json"

MEAN = (0.485, 0.456, 0.406)
STD  = (0.229, 0.224, 0.225)
SEED = 42
torch.manual_seed(SEED); np.random.seed(SEED)


def pick_device(name):
    if name == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    if name == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def make_transforms(img_size):
    train_tf = transforms.Compose([
        transforms.Resize((img_size + 24, img_size + 24)),
        transforms.RandomCrop(img_size),
        transforms.RandomHorizontalFlip(0.5),
        transforms.RandomRotation(15),
        transforms.RandAugment(num_ops=2, magnitude=7),
        transforms.ColorJitter(0.2, 0.2, 0.1),
        transforms.RandomApply([transforms.GaussianBlur(3, (0.1, 1.5))], p=0.2),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    return train_tf, eval_tf


def mixup(x, y, alpha=0.2):
    if alpha <= 0:
        return x, (y, y, 1.0)
    lam = np.random.beta(alpha, alpha)
    idx = torch.randperm(x.size(0), device=x.device)
    return lam * x + (1 - lam) * x[idx], (y, y[idx], lam)


def build_model(num_classes):
    return EfficientNet.from_pretrained('efficientnet-b0', num_classes=num_classes)


def set_trainable(model, classifier_only):
    for p in model.parameters():
        p.requires_grad = False
    for p in model._fc.parameters():
        p.requires_grad = True
    if not classifier_only:
        for p in model.parameters():
            p.requires_grad = True


class WarmupCosineLR(torch.optim.lr_scheduler._LRScheduler):
    def __init__(self, opt, warmup, total, min_lr=1e-7):
        self.warmup = max(1, warmup); self.total = max(self.warmup + 1, total)
        self.min_lr = min_lr; super().__init__(opt)

    def get_lr(self):
        e = self.last_epoch
        out = []
        for base in self.base_lrs:
            if e < self.warmup:
                out.append(base * (e + 1) / self.warmup)
            else:
                prog = (e - self.warmup) / max(1, self.total - self.warmup)
                out.append(self.min_lr + (base - self.min_lr) * 0.5 * (1 + math.cos(math.pi * prog)))
        return out


class _nullctx:
    def __enter__(self): return None
    def __exit__(self, *a): return False


@torch.no_grad()
def evaluate(model, loader, device, criterion):
    model.eval()
    ys, ps, losses = [], [], 0.0
    for x, y in loader:
        x = x.to(device, memory_format=torch.channels_last); y = y.to(device)
        out = model(x)
        losses += criterion(out, y).item() * x.size(0)
        ps.extend(out.argmax(1).cpu().tolist()); ys.extend(y.cpu().tolist())
    acc = accuracy_score(ys, ps)
    p, r, f, _ = precision_recall_fscore_support(ys, ps, average='macro', zero_division=0)
    return {'loss': losses / max(1, len(loader.dataset)), 'acc': acc,
            'macro_p': p, 'macro_r': r, 'macro_f1': f,
            'cm': confusion_matrix(ys, ps).tolist()}


def train_epoch(model, loader, device, criterion, opt, use_amp, mixup_alpha, accum, prefix):
    model.train()
    run, n = 0.0, 0
    bar = tqdm(loader, desc=prefix, ncols=110)
    opt.zero_grad(set_to_none=True)
    for step, (x, y) in enumerate(bar):
        x = x.to(device, memory_format=torch.channels_last); y = y.to(device)
        if mixup_alpha > 0:
            x, (ya, yb, lam) = mixup(x, y, mixup_alpha)
        amp_ctx = (torch.autocast(device_type=device.type, dtype=torch.float16)
                   if use_amp and device.type in ('mps', 'cuda') else _nullctx())
        with amp_ctx:
            out = model(x)
            if mixup_alpha > 0:
                loss = lam * criterion(out, ya) + (1 - lam) * criterion(out, yb)
            else:
                loss = criterion(out, y)
        (loss / accum).backward()
        if (step + 1) % accum == 0 or step == len(loader) - 1:
            opt.step(); opt.zero_grad(set_to_none=True)
        run += loss.item() * x.size(0); n += x.size(0)
        bar.set_postfix(loss=f"{run/max(1,n):.4f}")
        if device.type == 'mps' and step % 20 == 0:
            torch.mps.empty_cache()
    return run / max(1, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='mps', choices=['mps', 'cuda', 'cpu'])
    ap.add_argument('--img-size', type=int, default=224)
    ap.add_argument('--batch-size', type=int, default=16)
    ap.add_argument('--accum-steps', type=int, default=2)
    ap.add_argument('--phase1-epochs', type=int, default=4)
    ap.add_argument('--phase2-epochs', type=int, default=45)
    ap.add_argument('--phase1-lr', type=float, default=1e-3)
    ap.add_argument('--phase2-lr', type=float, default=1e-4)
    ap.add_argument('--weight-decay', type=float, default=1e-4)
    ap.add_argument('--label-smoothing', type=float, default=0.1)
    ap.add_argument('--mixup-alpha', type=float, default=0.2)
    ap.add_argument('--patience', type=int, default=5,
                    help='Early stop if val accuracy does not improve for this '
                         'many consecutive epochs (overfitting guard).')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--amp', action='store_true',
                    help='float16 autocast. Unstable on MPS — leave OFF on Mac.')
    ap.add_argument('--max-hours', type=float, default=4.0)
    ap.add_argument('--limit', type=int, default=0,
                    help='Smoke test: cap train+val to this many images per set.')
    args = ap.parse_args()

    train_start = time.time()
    budget_sec = args.max_hours * 3600

    def out_of_time():
        return budget_sec > 0 and (time.time() - train_start) >= budget_sec

    device = pick_device(args.device)
    print(f"🖥  device={device}  img={args.img_size}  batch={args.batch_size}"
          f"  accum={args.accum_steps}  eff_batch={args.batch_size*args.accum_steps}"
          f"  amp={args.amp}")

    train_tf, eval_tf = make_transforms(args.img_size)
    train_ds = datasets.ImageFolder(os.path.join(DATA_ROOT, 'train'), transform=train_tf)
    val_ds   = datasets.ImageFolder(os.path.join(DATA_ROOT, 'val'),   transform=eval_tf)
    classes = train_ds.classes
    num_classes = len(classes)
    print(f"📚 classes (idx): {classes}")
    print(f"📦 train={len(train_ds)}  val={len(val_ds)}")

    targets = np.array(train_ds.targets)
    counts = np.bincount(targets, minlength=num_classes)
    print(f"📊 train counts: {counts.tolist()}  imbalance={counts.max()/max(1,counts.min()):.2f}×")

    # WeightedRandomSampler (inverse-frequency)
    inv = 1.0 / (counts + 1e-9)
    sample_w = inv[targets]

    # Optional smoke-test subset
    if args.limit > 0:
        rng = np.random.default_rng(SEED)
        tr_idx = rng.choice(len(train_ds), size=min(args.limit, len(train_ds)), replace=False)
        va_idx = rng.choice(len(val_ds), size=min(args.limit, len(val_ds)), replace=False)
        train_ds = Subset(train_ds, tr_idx.tolist())
        val_ds = Subset(val_ds, va_idx.tolist())
        sample_w = sample_w[tr_idx]
        print(f"🔬 smoke test: train={len(train_ds)} val={len(val_ds)}")

    sampler = WeightedRandomSampler(sample_w.tolist(), len(sample_w), replacement=True)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler,
                              num_workers=args.workers, pin_memory=False,
                              drop_last=True, persistent_workers=args.workers > 0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                            num_workers=args.workers, pin_memory=False,
                            persistent_workers=args.workers > 0)

    criterion = nn.CrossEntropyLoss(label_smoothing=args.label_smoothing)
    model = build_model(num_classes).to(device, memory_format=torch.channels_last)

    os.makedirs(os.path.dirname(OUT_WEIGHTS), exist_ok=True)
    log = {'phase1': [], 'phase2': []}
    best_acc, no_improve = 0.0, 0

    def save_best(val, tag, ep):
        payload = {
            'model_state_dict': {k: v.detach().cpu() for k, v in model.state_dict().items()},
            'classes': classes,
            'class_to_idx': {c: i for i, c in enumerate(classes)},
            'best_val_acc': val['acc'], 'best_val_macro_f1': val['macro_f1'],
            'img_size': args.img_size, 'arch': 'efficientnet-b0',
            'normalize_mean': list(MEAN), 'normalize_std': list(STD),
            'saved_at': f'{tag}:epoch{ep}',
        }
        tmp = OUT_WEIGHTS + '.tmp'
        torch.save(payload, tmp); os.replace(tmp, OUT_WEIGHTS)
        with open(OUT_LOG, 'w') as f:
            json.dump({'config': vars(args), 'log': log,
                       'best_val_acc': val['acc'], 'classes': classes}, f, indent=2)

    # ── Phase 1 — head only ──
    print("\n══ Phase 1 ══ _fc head only")
    set_trainable(model, classifier_only=True)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                            lr=args.phase1_lr, weight_decay=args.weight_decay)
    for ep in range(args.phase1_epochs):
        tl = train_epoch(model, train_loader, device, criterion, opt,
                         args.amp, 0.0, args.accum_steps, f'P1[{ep+1}/{args.phase1_epochs}]')
        val = evaluate(model, val_loader, device, criterion)
        print(f"  train {tl:.4f} | val loss {val['loss']:.4f} acc {val['acc']:.4f} f1 {val['macro_f1']:.4f}")
        log['phase1'].append({'epoch': ep+1, 'train_loss': tl, **val})
        if val['acc'] > best_acc:
            best_acc = val['acc']; save_best(val, 'phase1', ep+1)
            print(f"  💾 new best {best_acc:.4f} → {OUT_WEIGHTS}")
        if out_of_time():
            print("⏱  budget reached during Phase 1 — stopping.")
            print(f"\n✅ best val acc {best_acc:.4f} → {OUT_WEIGHTS}")
            return

    # ── Phase 2 — full fine-tune ──
    print("\n══ Phase 2 ══ full fine-tune (cosine + warmup)")
    set_trainable(model, classifier_only=False)
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  trainable params: {n_train/1e6:.1f}M")
    opt = torch.optim.AdamW(model.parameters(), lr=args.phase2_lr, weight_decay=args.weight_decay)
    sched = WarmupCosineLR(opt, 4, args.phase2_epochs)
    if device.type == 'mps':
        torch.mps.empty_cache()
    for ep in range(args.phase2_epochs):
        tl = train_epoch(model, train_loader, device, criterion, opt,
                         args.amp, args.mixup_alpha, args.accum_steps,
                         f'P2[{ep+1}/{args.phase2_epochs}]')
        if device.type == 'mps':
            torch.mps.empty_cache()
        val = evaluate(model, val_loader, device, criterion)
        sched.step()
        lr = opt.param_groups[0]['lr']
        print(f"  train {tl:.4f} | val loss {val['loss']:.4f} acc {val['acc']:.4f} "
              f"f1 {val['macro_f1']:.4f} | lr {lr:.2e}")
        log['phase2'].append({'epoch': ep+1, 'train_loss': tl, 'lr': lr, **val})
        if val['acc'] > best_acc:
            best_acc = val['acc']; save_best(val, 'phase2', ep+1); no_improve = 0
            print(f"  💾 new best {best_acc:.4f} → {OUT_WEIGHTS}")
        else:
            no_improve += 1
            if no_improve >= args.patience:
                print(f"⏹  early stop (no improve {no_improve} epochs)")
                break
        elapsed_h = (time.time() - train_start) / 3600
        print(f"     ⏱  elapsed {elapsed_h:.2f}h / {args.max_hours}h budget")
        if out_of_time():
            print("⏱  budget reached — stopping cleanly.")
            break

    print(f"\n✅ best val acc {best_acc:.4f} → {OUT_WEIGHTS}")
    print(f"📈 log → {OUT_LOG}")
    print("   Next: evaluate with  python scripts/evaluate_scalp.py")


if __name__ == '__main__':
    main()
