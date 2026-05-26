"""
scripts/train_normal_binary_mps.py
──────────────────────────────────
Trains a SPECIALIST EfficientNet-B0 binary classifier that predicts only:
    class 0 = normal
    class 1 = abnormal  (acne ∪ dark_spots ∪ dryness)

This is the second model in an ensemble-of-specialists architecture. The
existing EfficientNet-B4 (4-class) is NOT touched. At inference the pipeline
will use B4 for the disease distribution and B0 for the normal probability.

Why B0 instead of B4 for this job:
    • 5.3 M parameters (vs 19 M for B4)  → 4× faster
    • 224×224 input (vs 380)              → ~3× less memory
    • Binary task is much easier than multiclass → less data needed
    • Whole training run fits comfortably in 8 GB Mac M1 MPS in 1.5–2 hours

Run:
    cd "/Users/alihassan/Desktop/fyp devlopment be"
    source venv/bin/activate
    python scripts/train_normal_binary_mps.py --epochs 15
"""
from __future__ import annotations
import argparse
import os
import random
import time
from collections import Counter

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import datasets, transforms
from efficientnet_pytorch import EfficientNet
from tqdm import tqdm

# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRAIN_DIR    = os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/train")
VAL_DIR      = os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/val")
OUTPUT_PATH  = os.path.join(PROJECT_ROOT, "core/ai_models/efficientnet_b0_normal_binary.pth")

# ── 8 GB MPS-safe defaults ──────────────────────────────────────────────
DEFAULT_BATCH    = 16
DEFAULT_EPOCHS   = 15
DEFAULT_LR       = 3e-4
DEFAULT_IMG_SIZE = 224
DEFAULT_PATIENCE = 4
SEED = 42


def get_device(force_cpu: bool = False) -> torch.device:
    if force_cpu:
        return torch.device("cpu")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# Wrap ImageFolder so that the 4 disease/normal folders become a binary task.
class BinaryNormalWrapper(Dataset):
    """
    Re-maps ImageFolder labels into:
        normal → 0
        anything else → 1
    """
    def __init__(self, image_folder: datasets.ImageFolder):
        self.inner = image_folder
        self.classes = ["normal", "abnormal"]
        # Find which raw index corresponds to the "normal" folder
        try:
            self.normal_raw_idx = image_folder.class_to_idx["normal"]
        except KeyError:
            raise RuntimeError(
                f"'normal' folder not found in {image_folder.root}. "
                f"Available: {list(image_folder.class_to_idx)}"
            )

    def __len__(self):
        return len(self.inner)

    def __getitem__(self, i):
        img, raw_label = self.inner[i]
        new_label = 0 if raw_label == self.normal_raw_idx else 1
        return img, new_label


def build_transforms(img_size: int):
    train_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.RandomAffine(degrees=0, translate=(0.05, 0.05)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return train_tf, val_tf


def eval_loop(model, loader, device):
    model.eval()
    tp = fp = fn = tn = 0
    total = correct = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)
            logits = model(x)
            pred = logits.argmax(1)
            for p, t in zip(pred.tolist(), y.tolist()):
                if p == 0 and t == 0: tn += 1     # true normal
                elif p == 1 and t == 1: tp += 1   # true abnormal
                elif p == 0 and t == 1: fn += 1   # missed abnormal
                else: fp += 1                     # false alarm
            correct += (pred == y).sum().item()
            total   += y.size(0)
    acc = 100.0 * correct / max(total, 1)
    # Treat "normal" as the positive class for clarity
    p_normal_precision = tn / max(tn + fn, 1)
    p_normal_recall    = tn / max(tn + fp, 1)
    return acc, p_normal_precision, p_normal_recall, (tp, fp, fn, tn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-dir", default=TRAIN_DIR)
    ap.add_argument("--val-dir",   default=VAL_DIR)
    ap.add_argument("--epochs",    type=int, default=DEFAULT_EPOCHS)
    ap.add_argument("--batch",     type=int, default=DEFAULT_BATCH)
    ap.add_argument("--lr",        type=float, default=DEFAULT_LR)
    ap.add_argument("--img-size",  type=int, default=DEFAULT_IMG_SIZE)
    ap.add_argument("--patience",  type=int, default=DEFAULT_PATIENCE)
    ap.add_argument("--out",       default=OUTPUT_PATH)
    ap.add_argument("--cpu",       action="store_true")
    ap.add_argument("--yes",       action="store_true")
    args = ap.parse_args()

    random.seed(SEED); torch.manual_seed(SEED)
    device = get_device(args.cpu)
    print(f"━━ Device: {device.type.upper()} ━━")

    train_tf, val_tf = build_transforms(args.img_size)

    train_raw = datasets.ImageFolder(args.train_dir, transform=train_tf)
    val_raw   = datasets.ImageFolder(args.val_dir,   transform=val_tf)
    train_ds  = BinaryNormalWrapper(train_raw)
    val_ds    = BinaryNormalWrapper(val_raw)

    # Count per binary class
    binary_counts = Counter()
    for _, _, label in [(i, *train_ds[i]) for i in range(0)]:
        pass
    train_labels = [0 if r == train_ds.normal_raw_idx else 1
                    for _, r in train_raw.samples]
    val_labels   = [0 if r == val_ds.normal_raw_idx else 1
                    for _, r in val_raw.samples]
    print(f"Train: normal={train_labels.count(0)}  abnormal={train_labels.count(1)}")
    print(f"Val:   normal={val_labels.count(0)}  abnormal={val_labels.count(1)}")

    # WeightedRandomSampler so each batch is class-balanced on average
    n0 = train_labels.count(0)
    n1 = train_labels.count(1)
    weights = [1.0 / n0 if l == 0 else 1.0 / n1 for l in train_labels]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=args.batch, sampler=sampler,
                              num_workers=0, pin_memory=False)
    val_loader   = DataLoader(val_ds, batch_size=args.batch, shuffle=False,
                              num_workers=0, pin_memory=False)

    # ── Model: EfficientNet-B0 with 2-class head ─────────────────────────
    model = EfficientNet.from_pretrained("efficientnet-b0")
    model._fc = nn.Linear(model._fc.in_features, 2)
    model = model.to(device)

    # Class weights as additional safety (already balanced via sampler, but
    # explicit weights help calibrate gradient magnitude).
    cls_weights = torch.tensor([n0 + n1] * 2, dtype=torch.float32, device=device)
    cls_weights[0] = (n0 + n1) / max(n0, 1)
    cls_weights[1] = (n0 + n1) / max(n1, 1)
    criterion = nn.CrossEntropyLoss(weight=cls_weights, label_smoothing=0.05)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    print("\n━━ Config ━━")
    print(f"  epochs={args.epochs}  batch={args.batch}  lr={args.lr}")
    print(f"  img_size={args.img_size}  patience={args.patience}")
    print(f"  out={args.out}\n")
    if not args.yes:
        ans = input("Start training? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted.")
            return

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    best_val = 0.0
    no_improve = 0

    for ep in range(args.epochs):
        t0 = time.time()
        model.train()
        loss_acc = 0.0
        n_correct = n_total = 0

        for x, y in tqdm(train_loader, desc=f"Epoch {ep+1}/{args.epochs} train"):
            x = x.to(device); y = y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            loss_acc += loss.item()
            n_correct += (logits.argmax(1) == y).sum().item()
            n_total   += y.size(0)
        scheduler.step()

        train_acc = 100.0 * n_correct / max(n_total, 1)
        avg_loss  = loss_acc / max(len(train_loader), 1)
        val_acc, p_prec, p_rec, (tp, fp, fn, tn) = eval_loop(model, val_loader, device)
        elapsed = time.time() - t0

        print(f"  ⏱ {elapsed:.1f}s  train_loss={avg_loss:.4f}  train_acc={train_acc:.2f}%  val_acc={val_acc:.2f}%")
        print(f"     normal precision={p_prec:.3f}  recall={p_rec:.3f}    TN={tn} FP={fp} FN={fn} TP={tp}")

        if val_acc > best_val:
            best_val = val_acc
            no_improve = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "classes": ["normal", "abnormal"],
                "img_size": args.img_size,
                "val_acc": val_acc,
                "normal_precision": p_prec,
                "normal_recall": p_rec,
                "epoch": ep + 1,
            }, args.out)
            print(f"  ★ Best saved → {args.out}  ({val_acc:.2f}%)")
        else:
            no_improve += 1
            print(f"  · no improvement ({no_improve}/{args.patience})")
            if no_improve >= args.patience:
                print("  ■ Early stopping.")
                break

    print(f"\n━━ Done. Best val_acc = {best_val:.2f}% ━━")
    print(f"  → {args.out}")
    print("\nNext: restart Django. The pipeline will auto-detect this file and")
    print("use it alongside the existing EfficientNet-B4. No manual promotion")
    print("step is needed (the existing 4-class model is never touched).")


if __name__ == "__main__":
    main()
