"""
train_dryness_v2.py
───────────────────
Train a dryness-only EfficientNet-B4 binary classifier (dry vs not_dry)
on the killa92/facial-skin-analysis-and-type-classification dataset.

Spec (per request, maximised for accuracy):
  • Model: EfficientNet-B4, fine-tune.
  • Phase 1: train classifier head only, 5 epochs, lr=1e-3.
  • Phase 2: unfreeze all, lr=1e-4 with cosine annealing.
  • Optimizer: AdamW (weight_decay=1e-4).
  • Loss: CrossEntropyLoss(label_smoothing=0.1) + class-weight rebalance.
  • LR scheduler: CosineAnnealingLR with 5-epoch linear warmup (Phase 2).
  • Early stopping: patience=10 on val loss.
  • Augmentation: hflip, rotation±15°, brightness/contrast±0.2, Gaussian blur, MixUp.
  • Batch size: 32, max epochs: 50.
  • Imbalance: WeightedRandomSampler.
  • Checkpoint: best val accuracy only → core/ai_models/dryness_v2.pth.
  • DOES NOT touch the existing efficientnet_b4_skin.pth file.

Outputs:
  • core/ai_models/dryness_v2.pth   (best val-accuracy weights)
  • training_log_dryness_v2.json    (per-epoch metrics)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from contextlib import nullcontext
from typing import List

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms
from torchvision.models import efficientnet_b4, EfficientNet_B4_Weights
from sklearn.metrics import precision_recall_fscore_support, accuracy_score, confusion_matrix
from tqdm import tqdm


# ── Paths ───────────────────────────────────────────────────────────
DATASET_ROOT = "dataset/efficientnet_b4/dryness"
TRAIN_DIR    = f"{DATASET_ROOT}/train"
VAL_DIR      = f"{DATASET_ROOT}/val"
TEST_DIR     = f"{DATASET_ROOT}/test"
OUT_WEIGHTS  = "core/ai_models/dryness_v2.pth"
OUT_LOG      = "training_log_dryness_v2.json"


# ── Reproducibility ─────────────────────────────────────────────────
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)


def pick_device(name: str) -> torch.device:
    if name == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    if name == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# ── Transforms ──────────────────────────────────────────────────────
# EfficientNet-B4 native input is 380×380. We default to 224×224 so the
# whole model (including full unfreeze in Phase 2) fits inside Apple
# MPS's 9 GB allocator at batch 16. Override via --img-size if you have
# a larger GPU. The torchvision-recommended preprocessing transforms
# (mean / std) are used.
IMG_SIZE_DEFAULT = 224
MEAN = (0.485, 0.456, 0.406)
STD  = (0.229, 0.224, 0.225)


def make_transforms(img_size: int):
    train_tf = transforms.Compose([
        transforms.Resize((img_size + 16, img_size + 16)),
        transforms.RandomCrop(img_size),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
        transforms.RandomApply([transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.5))], p=0.25),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    return train_tf, eval_tf


# ── MixUp (vectorised) ──────────────────────────────────────────────
def mixup(images: torch.Tensor, targets: torch.Tensor, alpha: float = 0.2):
    """Returns mixed images and a soft-target tuple (y_a, y_b, lam)."""
    if alpha <= 0:
        return images, (targets, targets, 1.0)
    lam = np.random.beta(alpha, alpha)
    idx = torch.randperm(images.size(0), device=images.device)
    mixed = lam * images + (1 - lam) * images[idx]
    return mixed, (targets, targets[idx], lam)


def mixup_loss(criterion, logits, y_a, y_b, lam):
    return lam * criterion(logits, y_a) + (1 - lam) * criterion(logits, y_b)


# ── Build model ─────────────────────────────────────────────────────
def build_model(num_classes: int = 2) -> nn.Module:
    weights = EfficientNet_B4_Weights.IMAGENET1K_V1
    model = efficientnet_b4(weights=weights)
    # Replace classifier with a 2-class head.
    in_feat = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_feat, num_classes),
    )
    return model


def set_requires_grad(model: nn.Module, last_n_blocks: int, classifier_only: bool):
    """
    Phase 1: classifier_only=True  → freeze everything except classifier.
    Phase 2: classifier_only=False → unfreeze last_n_blocks + classifier;
                                     earlier layers stay frozen.
                                     last_n_blocks=None ⇒ unfreeze everything.
    """
    for p in model.parameters():
        p.requires_grad = False

    # EfficientNet-B4 features is a Sequential of 9 blocks (0-8).
    if classifier_only:
        for p in model.classifier.parameters():
            p.requires_grad = True
    else:
        for p in model.classifier.parameters():
            p.requires_grad = True
        if last_n_blocks is None:
            for p in model.features.parameters():
                p.requires_grad = True
        else:
            total = len(model.features)
            for i in range(max(0, total - last_n_blocks), total):
                for p in model.features[i].parameters():
                    p.requires_grad = True


# ── Warmup + cosine LR scheduler ─────────────────────────────────────
class WarmupCosineLR(torch.optim.lr_scheduler._LRScheduler):
    def __init__(self, optimizer, warmup_epochs: int, total_epochs: int, min_lr: float = 1e-7):
        self.warmup = max(1, warmup_epochs)
        self.total  = max(self.warmup + 1, total_epochs)
        self.min_lr = min_lr
        super().__init__(optimizer)

    def get_lr(self):
        # epoch is set via scheduler.step() once per epoch.
        e = self.last_epoch
        return [self._lr_for(base, e) for base in self.base_lrs]

    def _lr_for(self, base, e):
        if e < self.warmup:
            return base * (e + 1) / self.warmup
        progress = (e - self.warmup) / max(1, (self.total - self.warmup))
        cos = 0.5 * (1 + math.cos(math.pi * progress))
        return self.min_lr + (base - self.min_lr) * cos


# ── Train / eval loops ─────────────────────────────────────────────
def evaluate(model, loader, device, criterion):
    model.eval()
    losses, ys, ps = [], [], []
    with torch.no_grad():
        for imgs, ys_batch in loader:
            imgs, ys_batch = imgs.to(device), ys_batch.to(device)
            logits = model(imgs)
            losses.append(criterion(logits, ys_batch).item() * imgs.size(0))
            preds = logits.argmax(dim=1)
            ys.extend(ys_batch.cpu().numpy().tolist())
            ps.extend(preds.cpu().numpy().tolist())
    loss = sum(losses) / max(1, len(loader.dataset))
    acc = accuracy_score(ys, ps)
    p, r, f, _ = precision_recall_fscore_support(ys, ps, average='binary', pos_label=0, zero_division=0)
    # also macro for balance
    pM, rM, fM, _ = precision_recall_fscore_support(ys, ps, average='macro', zero_division=0)
    return {
        'loss': loss, 'acc': acc,
        'prec_dry': p, 'rec_dry': r, 'f1_dry': f,
        'prec_macro': pM, 'rec_macro': rM, 'f1_macro': fM,
        'cm': confusion_matrix(ys, ps).tolist(),
    }


def train_one_epoch(model, loader, device, criterion, optimizer,
                     mixup_alpha=0.2, accum_steps=1, log_prefix=''):
    """Trains one epoch with optional gradient accumulation.
    Effective batch = loader.batch_size × accum_steps."""
    model.train()
    running, n = 0.0, 0
    bar = tqdm(loader, desc=log_prefix, ncols=110)
    optimizer.zero_grad(set_to_none=True)
    for step, (imgs, ys) in enumerate(bar):
        imgs, ys = imgs.to(device), ys.to(device)
        if mixup_alpha > 0:
            mixed, (ya, yb, lam) = mixup(imgs, ys, alpha=mixup_alpha)
            logits = model(mixed)
            loss = mixup_loss(criterion, logits, ya, yb, lam)
        else:
            logits = model(imgs)
            loss = criterion(logits, ys)
        (loss / accum_steps).backward()
        if (step + 1) % accum_steps == 0 or step == len(loader) - 1:
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
        running += loss.item() * imgs.size(0)
        n += imgs.size(0)
        bar.set_postfix(loss=f"{running/max(1,n):.4f}")
        # Help the MPS allocator reuse pages between batches.
        if torch.backends.mps.is_available() and (step % 20 == 0):
            torch.mps.empty_cache()
    return running / max(1, n)


# ── Main entrypoint ─────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='mps', choices=['mps', 'cuda', 'cpu'])
    # Effective batch 32 = per-step 16 × accum 2. Fits ~7.5 GB on MPS
    # during Phase 2 (full unfreeze of EfficientNet-B4 @ 224×224).
    ap.add_argument('--batch-size',  type=int, default=16)
    ap.add_argument('--accum-steps', type=int, default=2,
                    help='Gradient accumulation steps. effective_batch = batch * accum.')
    ap.add_argument('--img-size',    type=int, default=IMG_SIZE_DEFAULT,
                    help='Square crop size. 224 fits 9GB MPS; 256+ requires more VRAM.')
    ap.add_argument('--phase1-epochs', type=int, default=5)
    ap.add_argument('--phase2-epochs', type=int, default=45,
                    help='Phase 2 max epochs; total ≤ 50.')
    ap.add_argument('--phase1-lr', type=float, default=1e-3)
    ap.add_argument('--phase2-lr', type=float, default=1e-4)
    ap.add_argument('--weight-decay', type=float, default=1e-4)
    ap.add_argument('--label-smoothing', type=float, default=0.1)
    ap.add_argument('--mixup-alpha', type=float, default=0.2)
    ap.add_argument('--patience', type=int, default=10)
    ap.add_argument('--workers', type=int, default=0)
    # Rebalance strategy — only one at a time (using both double-weights
    # the minority class and degrades accuracy).
    ap.add_argument('--rebalance', default='sampler',
                    choices=['sampler', 'loss_weight', 'none'])
    args = ap.parse_args(argv)

    device = pick_device(args.device)
    print(f'🖥  Device: {device}')

    train_tf, eval_tf = make_transforms(args.img_size)
    train_ds = datasets.ImageFolder(TRAIN_DIR, transform=train_tf)
    val_ds   = datasets.ImageFolder(VAL_DIR,   transform=eval_tf)
    print(f'📚 Classes: {train_ds.classes}  (0=dry / 1=not_dry)')
    print(f'📦 Train: {len(train_ds)}   Val: {len(val_ds)}')
    print(f'🖼  Image size: {args.img_size}×{args.img_size}'
          f'   batch={args.batch_size}  accum={args.accum_steps}'
          f'   (effective batch={args.batch_size*args.accum_steps})')

    targets = np.array([y for _, y in train_ds.samples])
    class_counts = np.bincount(targets)
    print(f'📊 Train class counts: {class_counts.tolist()}  rebalance="{args.rebalance}"')

    # Rebalance strategy: pick ONE (sampler OR loss_weight). Doing both
    # double-weights the minority class and tanks accuracy.
    if args.rebalance == 'sampler':
        inv = 1.0 / (class_counts + 1e-9)
        sample_weights = inv[targets]
        sampler = WeightedRandomSampler(
            weights=sample_weights.tolist(),
            num_samples=len(sample_weights),
            replacement=True,
        )
        loss_weight_tensor = None
        train_loader = DataLoader(
            train_ds, batch_size=args.batch_size, sampler=sampler,
            num_workers=args.workers, pin_memory=False, drop_last=True,
        )
    else:
        # Either 'none' or 'loss_weight'.
        train_loader = DataLoader(
            train_ds, batch_size=args.batch_size, shuffle=True,
            num_workers=args.workers, pin_memory=False, drop_last=True,
        )
        if args.rebalance == 'loss_weight':
            inv = 1.0 / (class_counts + 1e-9)
            w = inv / inv.sum() * len(class_counts)   # mean = 1
            loss_weight_tensor = torch.tensor(w, dtype=torch.float32, device=device)
        else:
            loss_weight_tensor = None

    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=args.workers, pin_memory=False,
    )

    criterion = nn.CrossEntropyLoss(weight=loss_weight_tensor,
                                    label_smoothing=args.label_smoothing)

    model = build_model(num_classes=2).to(device)

    # ── PHASE 1 — train classifier head only ──
    print('\n══ Phase 1 ══ classifier head only')
    set_requires_grad(model, last_n_blocks=None, classifier_only=True)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.phase1_lr, weight_decay=args.weight_decay,
    )

    best_acc, best_state, no_improve = 0.0, None, 0
    log = {'phase1': [], 'phase2': []}
    start = time.time()

    # ── Incremental save helper ──
    # Persists best weights to disk EVERY time a new best is found, so
    # an exception (or Ctrl-C) at any later point can never lose the
    # trained model again.
    os.makedirs(os.path.dirname(OUT_WEIGHTS), exist_ok=True)

    def save_best(state_dict_cpu, val_metrics, phase_tag, epoch_idx):
        payload = {
            'state_dict':     state_dict_cpu,
            'classes':        train_ds.classes,
            'best_val_acc':   val_metrics['acc'],
            'best_val_f1_dry': val_metrics['f1_dry'],
            'img_size':       args.img_size,
            'normalize_mean': list(MEAN),
            'normalize_std':  list(STD),
            'spec': {
                'arch':            'efficientnet_b4',
                'num_classes':     2,
                'positive_label':  'dry (index 0)',
                'label_smoothing': args.label_smoothing,
                'mixup_alpha':     args.mixup_alpha,
                'rebalance':       args.rebalance,
                'saved_at_phase':  phase_tag,
                'saved_at_epoch':  epoch_idx,
            },
        }
        tmp = OUT_WEIGHTS + '.tmp'
        torch.save(payload, tmp)
        os.replace(tmp, OUT_WEIGHTS)
        # Also flush the log so it's always in sync with disk weights.
        with open(OUT_LOG, 'w') as f:
            json.dump({'config': vars(args), 'log': log,
                       'best_val_acc': val_metrics['acc'],
                       'classes': train_ds.classes}, f, indent=2)

    for epoch in range(args.phase1_epochs):
        prefix = f'P1 [{epoch+1}/{args.phase1_epochs}]'
        tr_loss = train_one_epoch(model, train_loader, device, criterion,
                                    optimizer, mixup_alpha=0.0,
                                    accum_steps=args.accum_steps, log_prefix=prefix)
        val = evaluate(model, val_loader, device, criterion)
        print(f'  ↳ train loss {tr_loss:.4f} | val loss {val["loss"]:.4f} '
              f'| val acc {val["acc"]:.4f} | f1_dry {val["f1_dry"]:.4f}')
        log['phase1'].append({'epoch': epoch + 1, 'train_loss': tr_loss, **val})
        if val['acc'] > best_acc:
            best_acc = val['acc']
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            save_best(best_state, val, 'phase1', epoch + 1)
            print(f'  💾 new best val acc: {best_acc:.4f}  →  saved {OUT_WEIGHTS}')

    # ── PHASE 2 — full fine-tune (last 3 blocks at first, then all) ──
    print('\n══ Phase 2 ══ full fine-tune (lr cosine + warmup)')
    set_requires_grad(model, last_n_blocks=None, classifier_only=False)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.phase2_lr, weight_decay=args.weight_decay,
    )
    scheduler = WarmupCosineLR(optimizer, warmup_epochs=5,
                                total_epochs=args.phase2_epochs)

    # Flush any Phase 1 allocator residue before Phase 2 unfreezes the
    # whole graph — this is what was hitting the 9 GB MPS ceiling.
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    for epoch in range(args.phase2_epochs):
        prefix = f'P2 [{epoch+1}/{args.phase2_epochs}]'
        tr_loss = train_one_epoch(model, train_loader, device, criterion,
                                    optimizer, mixup_alpha=args.mixup_alpha,
                                    accum_steps=args.accum_steps, log_prefix=prefix)
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        val = evaluate(model, val_loader, device, criterion)
        scheduler.step()
        cur_lr = optimizer.param_groups[0]['lr']
        print(f'  ↳ train loss {tr_loss:.4f} | val loss {val["loss"]:.4f} '
              f'| val acc {val["acc"]:.4f} | f1_dry {val["f1_dry"]:.4f} '
              f'| lr {cur_lr:.2e}')
        log['phase2'].append({'epoch': epoch + 1, 'train_loss': tr_loss,
                               'lr': cur_lr, **val})

        if val['acc'] > best_acc:
            best_acc = val['acc']
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            save_best(best_state, val, 'phase2', epoch + 1)
            no_improve = 0
            print(f'  💾 new best val acc: {best_acc:.4f}  →  saved {OUT_WEIGHTS}')
        else:
            no_improve += 1
            if no_improve >= args.patience:
                print(f'⏹  Early stopping after {no_improve} epochs without improvement.')
                break

    # ── Final summary ──
    # The best weights are ALREADY on disk thanks to incremental
    # save_best() — this section just prints the wrap-up. Even if any
    # exception happens here, the trained model is safe.
    elapsed = time.time() - start
    print(f'\n✅ Best weights persisted to: {OUT_WEIGHTS}')
    print(f'   best val acc: {best_acc:.4f}')
    print(f'   elapsed     : {elapsed/60:.1f} min')
    print(f'📈 Per-epoch log → {OUT_LOG}')


if __name__ == '__main__':
    main()
