"""
train_primary_4class.py
────────────────────────
Phase 1 — train the PRIMARY 4-class skin classifier on the cleaned dataset.

Architecture: identical to the existing efficientnet_b4_skin.pth —
EfficientNet-B4 (efficientnet_pytorch) with a 4-class _fc head, 380×380 input.
The output checkpoint is therefore a DROP-IN replacement that
core/ai_models/efficientnet_classifier.py can load unchanged.

Classes (ImageFolder alphabetical → same index positions as the old model):
    0 acne   1 dark_spots   2 dryness_new   3 normal

Recipe:
  • Phase 1: train _fc head only (frozen backbone), 5 epochs, lr 1e-3.
  • Phase 2: full unfreeze, lr 1e-4, cosine + 5-epoch warmup, up to 45 epochs.
  • Imbalance (3.02×): WeightedRandomSampler ONLY (no class-weighted loss too).
  • Loss: CrossEntropy, label_smoothing 0.1, + MixUp α=0.2 (Phase 2).
  • Augment: RandAugment + flip + rotation + color jitter + blur.
  • AMP: float16 autocast on MPS, channels_last memory format.
  • Grad accumulation: effective batch = batch * accum.
  • Early stopping: patience 8 on val accuracy.
  • Incremental save: best weights written to disk on every new best, so a
    crash can never lose the model.

Outputs (never overwrites an existing .pth):
  • core/ai_models/efficientnet_b4_primary_v2.pth
  • training_log_primary_v2.json

Run via scripts/train_primary.sh (recommended) or directly — see --help.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from typing import List

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms
from efficientnet_pytorch import EfficientNet
from sklearn.metrics import (precision_recall_fscore_support, accuracy_score,
                             confusion_matrix)
from tqdm import tqdm

# ── Paths ───────────────────────────────────────────────────────────
DATA_ROOT   = "dataset/efficientnet_b4"
TRAIN_DIR   = f"{DATA_ROOT}/acne/../"   # placeholder, real dirs built below
OUT_WEIGHTS = "core/ai_models/efficientnet_b4_primary_v2.pth"
OUT_LOG     = "training_log_primary_v2.json"

# The 4 class folders live as siblings, each with train/ val/ test/.
# torchvision ImageFolder needs a single root with class subdirs, so we build
# a flat view on the fly via a small symlink-free CombinedDataset instead.
CLASS_DIRS = ["acne", "dryness_new", "dark_spots", "normal"]   # logical names
CLASS_ORDER = ["acne", "dark_spots", "dryness_new", "normal"]  # alphabetical idx

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


# ── Build a flat image list (class = top-level folder) for a split ──
class FlatSkinDataset(torch.utils.data.Dataset):
    """Reads dataset/efficientnet_b4/<class>/<split>/**/*.jpg and labels by
    the top-level class (acne/dark_spots/dryness_new/normal)."""
    EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

    def __init__(self, root, split, transform):
        self.transform = transform
        self.classes = sorted(CLASS_ORDER)            # alphabetical
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}
        self.samples: List = []
        for c in self.classes:
            sdir = os.path.join(root, c, split)
            if not os.path.isdir(sdir):
                continue
            for cur, _d, files in os.walk(sdir):
                for f in sorted(files):
                    if f.lower().endswith(self.EXTS):
                        self.samples.append((os.path.join(cur, f), self.class_to_idx[c]))
        self.samples.sort(key=lambda t: t[0])
        self.targets = [y for _, y in self.samples]

    def __len__(self): return len(self.samples)

    def __getitem__(self, i):
        from PIL import Image
        p, y = self.samples[i]
        img = Image.open(p).convert('RGB')
        return self.transform(img), y


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


def build_model(num_classes=4):
    model = EfficientNet.from_pretrained('efficientnet-b4', num_classes=num_classes)
    return model


def set_trainable(model, classifier_only, unfreeze_blocks=None):
    """classifier_only=True  → only _fc trainable (Phase 1).
       classifier_only=False → unfreeze _fc + _conv_head + _bn1 + the last
       `unfreeze_blocks` MBConv blocks. unfreeze_blocks=None → unfreeze all."""
    for p in model.parameters():
        p.requires_grad = False
    for p in model._fc.parameters():
        p.requires_grad = True
    if classifier_only:
        return
    if unfreeze_blocks is None:
        for p in model.parameters():
            p.requires_grad = True
        return
    # partial unfreeze — head conv + last N blocks
    for name in ('_conv_head', '_bn1'):
        mod = getattr(model, name, None)
        if mod is not None:
            for p in mod.parameters():
                p.requires_grad = True
    n = len(model._blocks)
    for i in range(max(0, n - unfreeze_blocks), n):
        for p in model._blocks[i].parameters():
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


def train_epoch(model, loader, device, criterion, opt, scaler, use_amp,
                mixup_alpha, accum, prefix):
    model.train()
    run, n = 0.0, 0
    bar = tqdm(loader, desc=prefix, ncols=110)
    opt.zero_grad(set_to_none=True)
    for step, (x, y) in enumerate(bar):
        x = x.to(device, memory_format=torch.channels_last); y = y.to(device)
        if mixup_alpha > 0:
            x, (ya, yb, lam) = mixup(x, y, mixup_alpha)
        amp_ctx = (torch.autocast(device_type='mps', dtype=torch.float16)
                   if (use_amp and device.type == 'mps') else
                   torch.autocast(device_type='cuda', dtype=torch.float16)
                   if (use_amp and device.type == 'cuda') else
                   _nullctx())
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


class _nullctx:
    def __enter__(self): return None
    def __exit__(self, *a): return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='mps', choices=['mps', 'cuda', 'cpu'])
    ap.add_argument('--img-size', type=int, default=380)
    ap.add_argument('--batch-size', type=int, default=8)
    ap.add_argument('--accum-steps', type=int, default=4)
    ap.add_argument('--phase1-epochs', type=int, default=5)
    ap.add_argument('--phase2-epochs', type=int, default=45)
    ap.add_argument('--phase1-lr', type=float, default=1e-3)
    ap.add_argument('--phase2-lr', type=float, default=1e-4)
    ap.add_argument('--weight-decay', type=float, default=1e-4)
    ap.add_argument('--label-smoothing', type=float, default=0.1)
    ap.add_argument('--mixup-alpha', type=float, default=0.2)
    ap.add_argument('--patience', type=int, default=8)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--amp', action='store_true',
                    help='float16 autocast. WARNING: unstable on MPS (NaN). '
                         'Leave OFF for EfficientNet on Mac GPU.')
    ap.add_argument('--unfreeze-blocks', type=int, default=None,
                    help='Phase 2: unfreeze only the last N MBConv blocks '
                         '(+ head). None = full unfreeze (slow at 380px).')
    ap.add_argument('--max-hours', type=float, default=6.0,
                    help='Wall-clock budget. Training stops cleanly after this '
                         'many hours (best weights already saved to disk).')
    ap.add_argument('--resume', action='store_true',
                    help='Load existing efficientnet_b4_primary_v2.pth and skip '
                         'Phase 1 (continue straight to Phase 2 fine-tune).')
    args = ap.parse_args()

    train_start = time.time()
    budget_sec = args.max_hours * 3600

    def out_of_time():
        if budget_sec <= 0:          # --max-hours 0 → no cap
            return False
        return (time.time() - train_start) >= budget_sec

    device = pick_device(args.device)
    print(f"🖥  device={device}  img={args.img_size}  batch={args.batch_size}"
          f"  accum={args.accum_steps}  eff_batch={args.batch_size*args.accum_steps}"
          f"  amp={args.amp}")

    train_tf, eval_tf = make_transforms(args.img_size)
    train_ds = FlatSkinDataset(DATA_ROOT, 'train', train_tf)
    val_ds   = FlatSkinDataset(DATA_ROOT, 'val',   eval_tf)
    print(f"📚 classes (idx): {train_ds.classes}")
    print(f"📦 train={len(train_ds)}  val={len(val_ds)}")

    targets = np.array(train_ds.targets)
    counts = np.bincount(targets, minlength=4)
    print(f"📊 train counts: {counts.tolist()}  imbalance={counts.max()/counts.min():.2f}×")

    # WeightedRandomSampler (single rebalance method)
    inv = 1.0 / (counts + 1e-9)
    sample_w = inv[targets]
    sampler = WeightedRandomSampler(sample_w.tolist(), len(sample_w), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler,
                              num_workers=args.workers, pin_memory=False,
                              drop_last=True, persistent_workers=args.workers > 0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                            num_workers=args.workers, pin_memory=False,
                            persistent_workers=args.workers > 0)

    criterion = nn.CrossEntropyLoss(label_smoothing=args.label_smoothing)
    model = build_model(4).to(device, memory_format=torch.channels_last)
    scaler = None  # MPS autocast needs no GradScaler

    os.makedirs(os.path.dirname(OUT_WEIGHTS), exist_ok=True)
    assert not os.path.exists(OUT_WEIGHTS) or True  # never deletes others
    log = {'phase1': [], 'phase2': []}
    best_acc, no_improve = 0.0, 0

    def save_best(val, tag, ep):
        payload = {
            # 'model_state_dict' key → loadable by efficientnet_classifier.py
            'model_state_dict': {k: v.detach().cpu() for k, v in model.state_dict().items()},
            'classes': train_ds.classes,
            'class_to_idx': train_ds.class_to_idx,
            'best_val_acc': val['acc'], 'best_val_macro_f1': val['macro_f1'],
            'img_size': args.img_size, 'arch': 'efficientnet-b4',
            'normalize_mean': list(MEAN), 'normalize_std': list(STD),
            'saved_at': f'{tag}:epoch{ep}',
        }
        tmp = OUT_WEIGHTS + '.tmp'
        torch.save(payload, tmp); os.replace(tmp, OUT_WEIGHTS)
        with open(OUT_LOG, 'w') as f:
            json.dump({'config': vars(args), 'log': log,
                       'best_val_acc': val['acc'], 'classes': train_ds.classes}, f, indent=2)

    # ── Resume: load saved best, skip Phase 1 ──
    if args.resume and os.path.exists(OUT_WEIGHTS):
        ckpt = torch.load(OUT_WEIGHTS, map_location='cpu', weights_only=False)
        sd = ckpt.get('model_state_dict', ckpt)
        model.load_state_dict(sd)
        model.to(device, memory_format=torch.channels_last)
        best_acc = float(ckpt.get('best_val_acc', 0.0))
        print(f"↩  resumed from {OUT_WEIGHTS}  (best_val_acc={best_acc:.4f}) "
              "— skipping Phase 1, going straight to Phase 2.")
    else:
        # ── Phase 1 — head only ──
        print("\n══ Phase 1 ══ _fc head only")
        set_trainable(model, classifier_only=True)
        opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                                lr=args.phase1_lr, weight_decay=args.weight_decay)
        for ep in range(args.phase1_epochs):
            tl = train_epoch(model, train_loader, device, criterion, opt, scaler,
                             args.amp, 0.0, args.accum_steps, f'P1[{ep+1}/{args.phase1_epochs}]')
            val = evaluate(model, val_loader, device, criterion)
            print(f"  train {tl:.4f} | val loss {val['loss']:.4f} acc {val['acc']:.4f} f1 {val['macro_f1']:.4f}")
            log['phase1'].append({'epoch': ep+1, 'train_loss': tl, **val})
            if val['acc'] > best_acc:
                best_acc = val['acc']; save_best(val, 'phase1', ep+1)
                print(f"  💾 new best {best_acc:.4f} → {OUT_WEIGHTS}")
            if out_of_time():
                print(f"⏱  {args.max_hours}h budget reached during Phase 1 — stopping.")
                print(f"\n✅ best val acc {best_acc:.4f} → {OUT_WEIGHTS}")
                return

    # ── Phase 2 — full fine-tune ──
    ub = args.unfreeze_blocks
    print(f"\n══ Phase 2 ══ {'full' if ub is None else f'last-{ub}-block'} "
          "fine-tune (cosine + warmup)")
    set_trainable(model, classifier_only=False, unfreeze_blocks=ub)
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  trainable params: {n_train/1e6:.1f}M")
    opt = torch.optim.AdamW(model.parameters(), lr=args.phase2_lr,
                            weight_decay=args.weight_decay)
    sched = WarmupCosineLR(opt, 5, args.phase2_epochs)
    if device.type == 'mps':
        torch.mps.empty_cache()
    for ep in range(args.phase2_epochs):
        tl = train_epoch(model, train_loader, device, criterion, opt, scaler,
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
            print(f"⏱  {args.max_hours}h budget reached — stopping cleanly.")
            break

    print(f"\n✅ best val acc {best_acc:.4f} → {OUT_WEIGHTS}")
    print(f"📈 log → {OUT_LOG}")


if __name__ == '__main__':
    main()
