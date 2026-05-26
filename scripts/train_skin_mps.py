"""
scripts/train_skin_mps.py
─────────────────────────
EfficientNet-B4 skin-condition trainer optimized for Apple Silicon (MPS) on
an 8 GB Mac M1.

What this script does differently from the original train_efficientnet.py
─────────────────────────────────────────────────────────────────────────
1. Forces MPS device (Apple GPU) and prints a clear status line.
2. Caps the largest class (normal) by sub-sampling so the 4 classes are
   roughly balanced. This drops one epoch from ~90 minutes to ~25 minutes
   without losing generalisation, because the original 10,586 normal images
   were 10× larger than every other class.
3. Uses WeightedRandomSampler in addition to class weights — proper double
   protection against the remaining class imbalance.
4. Resumes from the existing efficientnet_b4_skin.pth automatically.
5. Saves best-validation checkpoint with metadata (epoch, val_acc, class list).
6. Per-class precision/recall printed at end of every epoch.
7. Early stopping with configurable patience (default 5).

Run:
    cd "/Users/alihassan/Desktop/fyp devlopment be"
    source venv/bin/activate
    python scripts/train_skin_mps.py --epochs 25
"""
from __future__ import annotations
import argparse
import os
import random
import shutil
import sys
import time
from datetime import datetime
from collections import Counter

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, WeightedRandomSampler, Subset
from torchvision import datasets, transforms
from efficientnet_pytorch import EfficientNet
from tqdm import tqdm

# ── Paths (relative to project root) ────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRAIN_DIR    = os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/train")
VAL_DIR      = os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/val")
ACTIVE_PATH  = os.path.join(PROJECT_ROOT, "core/ai_models/efficientnet_b4_skin.pth")
# Default OUTPUT_PATH writes a NEW file so the active model is never touched
# until you explicitly promote it (see scripts/promote_skin_model.py).
OUTPUT_PATH  = os.path.join(PROJECT_ROOT, "core/ai_models/efficientnet_b4_skin_v2.pth")
RESUME_PATHS = [
    ACTIVE_PATH,
    os.path.join(PROJECT_ROOT, "models/efficientnet_b4_skin.pth"),
]

# ── Defaults — 8 GB Mac M1 safe ────────────────────────────────────────
DEFAULT_BATCH      = 4
DEFAULT_EPOCHS     = 25
DEFAULT_LR         = 3e-5
DEFAULT_IMG_SIZE   = 380          # EfficientNet-B4 native (matches app inference)
DEFAULT_CAP_PER_CLS = 3500        # cap the largest class for balance + speed
DEFAULT_PATIENCE   = 5            # early stopping
SEED = 42


def get_mps_device(force_cpu: bool = False) -> torch.device:
    if force_cpu:
        return torch.device("cpu")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def build_transforms(img_size: int):
    train_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
        transforms.RandomAffine(degrees=0, translate=(0.05, 0.05)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.10)),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return train_tf, val_tf


def cap_dataset(ds: datasets.ImageFolder, cap: int) -> Subset:
    """Return a Subset where no class contributes more than `cap` samples."""
    if cap <= 0:
        return ds
    by_class: dict[int, list[int]] = {}
    for idx, (_, lbl) in enumerate(ds.samples):
        by_class.setdefault(lbl, []).append(idx)
    rng = random.Random(SEED)
    kept = []
    for lbl, idxs in by_class.items():
        if len(idxs) > cap:
            rng.shuffle(idxs)
            kept.extend(idxs[:cap])
        else:
            kept.extend(idxs)
    rng.shuffle(kept)
    return Subset(ds, kept)


def class_counts_from_indices(ds: datasets.ImageFolder, subset: Subset) -> Counter:
    return Counter(ds.samples[i][1] for i in subset.indices)


def per_class_eval(model, loader, device, num_classes):
    tp = [0] * num_classes
    fp = [0] * num_classes
    fn = [0] * num_classes
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            out = model(images)
            pred = out.argmax(1)
            for p, t in zip(pred.tolist(), labels.tolist()):
                if p == t:
                    tp[t] += 1
                else:
                    fp[p] += 1
                    fn[t] += 1
            correct += (pred == labels).sum().item()
            total += labels.size(0)
    acc = 100.0 * correct / max(total, 1)
    precisions, recalls = [], []
    for c in range(num_classes):
        p = tp[c] / max(tp[c] + fp[c], 1)
        r = tp[c] / max(tp[c] + fn[c], 1)
        precisions.append(p)
        recalls.append(r)
    return acc, precisions, recalls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-dir", default=TRAIN_DIR)
    ap.add_argument("--val-dir",   default=VAL_DIR)
    ap.add_argument("--epochs",    type=int, default=DEFAULT_EPOCHS)
    ap.add_argument("--batch",     type=int, default=DEFAULT_BATCH)
    ap.add_argument("--lr",        type=float, default=DEFAULT_LR)
    ap.add_argument("--img-size",  type=int, default=DEFAULT_IMG_SIZE)
    ap.add_argument("--cap",       type=int, default=DEFAULT_CAP_PER_CLS,
                    help="Cap per-class training samples (0 = no cap)")
    ap.add_argument("--patience",  type=int, default=DEFAULT_PATIENCE)
    ap.add_argument("--out",       default=OUTPUT_PATH)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--cpu",       action="store_true", help="Force CPU (debug)")
    ap.add_argument("--yes",       action="store_true")
    args = ap.parse_args()

    random.seed(SEED)
    torch.manual_seed(SEED)

    device = get_mps_device(force_cpu=args.cpu)
    print(f"━━ Device: {device.type.upper()} ━━")

    if not os.path.isdir(args.train_dir) or not os.path.isdir(args.val_dir):
        print(f"ERROR: dataset dirs missing.\n  train: {args.train_dir}\n  val:   {args.val_dir}")
        sys.exit(1)

    train_tf, val_tf = build_transforms(args.img_size)

    full_train = datasets.ImageFolder(args.train_dir, transform=train_tf)
    val_ds     = datasets.ImageFolder(args.val_dir,   transform=val_tf)
    class_names = full_train.classes
    num_classes = len(class_names)

    raw_counts = Counter(lbl for _, lbl in full_train.samples)
    print(f"Classes (n={num_classes}): {class_names}")
    print(f"Raw train counts: {[raw_counts[i] for i in range(num_classes)]}")

    train_ds = cap_dataset(full_train, args.cap)
    capped_counts = class_counts_from_indices(full_train, train_ds)
    print(f"Capped train counts (cap={args.cap}): {[capped_counts[i] for i in range(num_classes)]}")
    print(f"Train size after cap: {len(train_ds)}   Val size: {len(val_ds)}")

    # WeightedRandomSampler — every sample gets a weight inversely proportional
    # to its class frequency, so each batch is class-balanced on average.
    sample_weights = [1.0 / capped_counts[full_train.samples[i][1]] for i in train_ds.indices]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)

    train_loader = DataLoader(
        train_ds, batch_size=args.batch, sampler=sampler,
        num_workers=0, pin_memory=False,
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch, shuffle=False,
        num_workers=0, pin_memory=False,
    )

    # ── Model ──────────────────────────────────────────────────────────
    model = EfficientNet.from_pretrained("efficientnet-b4")
    model._fc = nn.Linear(model._fc.in_features, num_classes)
    model = model.to(device)

    if not args.no_resume:
        ckpt_path = next((p for p in RESUME_PATHS if os.path.isfile(p)), None)
        if ckpt_path:
            print(f"Resuming from: {ckpt_path}")
            try:
                ckpt = torch.load(ckpt_path, map_location=device)
                state = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt
                model.load_state_dict(state, strict=True)
                print("  ✓ Loaded prior weights")
            except Exception as e:
                print(f"  ✗ Could not load checkpoint ({e}); starting from ImageNet pre-trained.")
        else:
            print("No existing .pth found; starting from ImageNet pre-trained.")

    # ── Loss / optimiser ──────────────────────────────────────────────
    # Class weights (further protection against the remaining imbalance)
    weights = [sum(capped_counts.values()) / max(capped_counts[i], 1) for i in range(num_classes)]
    weights = torch.tensor(weights, dtype=torch.float32, device=device)
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=0.05)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    print("\n━━ Config ━━")
    print(f"  epochs={args.epochs} batch={args.batch} lr={args.lr}")
    print(f"  img_size={args.img_size} cap={args.cap} patience={args.patience}")
    print(f"  out={args.out}")
    if not args.yes:
        ans = input("\nStart training? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted.")
            return

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    # ── SAFETY: back up the currently active model before we start. ───
    if os.path.isfile(ACTIVE_PATH):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = ACTIVE_PATH.replace(".pth", f".backup_{ts}.pth")
        try:
            shutil.copy2(ACTIVE_PATH, backup_path)
            print(f"  ✓ Backed up active model → {backup_path}")
        except Exception as e:
            print(f"  ⚠ Could NOT back up active model: {e}")
            if not args.yes:
                ans = input("Proceed without backup? [y/N]: ").strip().lower()
                if ans not in ("y", "yes"):
                    print("Aborted.")
                    return

    # ── SAFETY: Evaluate the EXISTING active model on the val set first ──
    # so we have a baseline number to beat.
    baseline_val = None
    if os.path.isfile(ACTIVE_PATH) and not args.no_resume:
        print("\n  • Evaluating EXISTING active model on val set as baseline...")
        baseline_val, _, _ = per_class_eval(model, val_loader, device, num_classes)
        print(f"    Existing model val_acc = {baseline_val:.2f}%   (we must beat this to promote)")

    best_val = 0.0
    no_improve = 0

    for ep in range(args.epochs):
        t0 = time.time()
        model.train()
        train_loss = 0.0
        n_correct = n_total = 0

        for images, labels in tqdm(train_loader, desc=f"Epoch {ep+1}/{args.epochs} train"):
            images = images.to(device, non_blocking=False)
            labels = labels.to(device, non_blocking=False)
            optimizer.zero_grad()
            out = model(images)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            n_correct += (out.argmax(1) == labels).sum().item()
            n_total   += labels.size(0)

        scheduler.step()
        train_acc = 100.0 * n_correct / max(n_total, 1)
        avg_loss  = train_loss / max(len(train_loader), 1)

        val_acc, prec, rec = per_class_eval(model, val_loader, device, num_classes)
        elapsed = time.time() - t0
        print(f"  ⏱ {elapsed:.1f}s  train_loss={avg_loss:.4f}  train_acc={train_acc:.2f}%  val_acc={val_acc:.2f}%")
        for c in range(num_classes):
            print(f"     {class_names[c]:<12}  precision={prec[c]:.3f}  recall={rec[c]:.3f}")

        if val_acc > best_val:
            best_val = val_acc
            no_improve = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "class_names": class_names,
                "val_acc": val_acc,
                "epoch": ep + 1,
                "img_size": args.img_size,
            }, args.out)
            print(f"  ★ Best model saved to {args.out}  (val_acc={val_acc:.2f}%)")
        else:
            no_improve += 1
            print(f"  · no improvement ({no_improve}/{args.patience})")
            if no_improve >= args.patience:
                print(f"  ■ Early stopping triggered (no improvement for {args.patience} epochs).")
                break

    print(f"\n━━ Done. Best val_acc = {best_val:.2f}%  →  {args.out} ━━")
    if baseline_val is not None:
        delta = best_val - baseline_val
        verdict = "BETTER" if delta > 0 else ("EQUAL" if abs(delta) < 0.1 else "WORSE")
        print(f"   Baseline (active model) val_acc = {baseline_val:.2f}%")
        print(f"   Δ = {delta:+.2f}pp   →  new model is {verdict} than active.")
        if delta > 0:
            print(f"\n   To PROMOTE the new model into production:")
            print(f"   python scripts/promote_skin_model.py")
        else:
            print(f"\n   Recommendation: keep the existing active model. The new file at")
            print(f"   {args.out}")
            print(f"   can be safely deleted, or kept for further experimentation.")


if __name__ == "__main__":
    main()
