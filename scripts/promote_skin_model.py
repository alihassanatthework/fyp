"""
scripts/promote_skin_model.py
─────────────────────────────
Compares the newly-trained model (`efficientnet_b4_skin_v2.pth`) against the
currently-active model (`efficientnet_b4_skin.pth`) on the validation set.

Only if the new model is BETTER (or you pass --force) does it promote the new
file into the active path. The previous active model is backed up with a
timestamp suffix so you can roll back at any time.

Run:
    cd "/Users/alihassan/Desktop/fyp devlopment be"
    source venv/bin/activate
    python scripts/promote_skin_model.py            # compare + ask
    python scripts/promote_skin_model.py --force    # promote unconditionally
    python scripts/promote_skin_model.py --rollback # restore most recent backup
"""
from __future__ import annotations
import argparse
import glob
import os
import shutil
import sys
from datetime import datetime

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from efficientnet_pytorch import EfficientNet

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ACTIVE_PATH  = os.path.join(PROJECT_ROOT, "core/ai_models/efficientnet_b4_skin.pth")
NEW_PATH     = os.path.join(PROJECT_ROOT, "core/ai_models/efficientnet_b4_skin_v2.pth")
VAL_DIR      = os.path.join(PROJECT_ROOT, "dataset/efficientnet_b4/val")
IMG_SIZE     = 380


def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_state(path: str) -> dict:
    ckpt = torch.load(path, map_location="cpu")
    if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
        return ckpt["model_state_dict"]
    return ckpt


def eval_model(state_dict, val_dir, num_classes, device):
    tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    ds = datasets.ImageFolder(val_dir, transform=tf)
    loader = DataLoader(ds, batch_size=4, shuffle=False, num_workers=0)

    model = EfficientNet.from_pretrained("efficientnet-b4")
    model._fc = nn.Linear(model._fc.in_features, num_classes)
    model.load_state_dict(state_dict, strict=True)
    model.to(device).eval()

    tp = [0] * num_classes
    fp = [0] * num_classes
    fn = [0] * num_classes
    correct = total = 0
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            pred = model(images).argmax(1)
            for p, t in zip(pred.tolist(), labels.tolist()):
                if p == t:
                    tp[t] += 1
                else:
                    fp[p] += 1
                    fn[t] += 1
            correct += (pred == labels).sum().item()
            total += labels.size(0)
    acc = 100.0 * correct / max(total, 1)
    per_class = []
    for c in range(num_classes):
        p = tp[c] / max(tp[c] + fp[c], 1)
        r = tp[c] / max(tp[c] + fn[c], 1)
        per_class.append((ds.classes[c], p, r))
    return acc, per_class


def rollback():
    backups = sorted(glob.glob(ACTIVE_PATH.replace(".pth", ".backup_*.pth")), reverse=True)
    if not backups:
        print("No backups found.")
        return
    print("Available backups (most recent first):")
    for i, b in enumerate(backups):
        print(f"  [{i}] {os.path.basename(b)}")
    sel = input(f"Restore which? [0-{len(backups)-1}] (default 0): ").strip()
    try:
        idx = int(sel) if sel else 0
    except ValueError:
        idx = 0
    target = backups[idx]
    shutil.copy2(target, ACTIVE_PATH)
    print(f"✓ Restored {target}  →  {ACTIVE_PATH}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Promote unconditionally")
    ap.add_argument("--rollback", action="store_true", help="Restore a backup")
    args = ap.parse_args()

    if args.rollback:
        rollback()
        return

    if not os.path.isfile(NEW_PATH):
        print(f"ERROR: trained model not found at {NEW_PATH}")
        print("Run scripts/train_skin_mps.py first.")
        sys.exit(1)

    device = get_device()
    print(f"Device: {device.type.upper()}")

    # Probe val_dir for class count
    classes = sorted(d for d in os.listdir(VAL_DIR) if os.path.isdir(os.path.join(VAL_DIR, d)))
    n = len(classes)
    print(f"Classes ({n}): {classes}")

    print(f"\n• Evaluating ACTIVE  : {ACTIVE_PATH}")
    active_state = load_state(ACTIVE_PATH) if os.path.isfile(ACTIVE_PATH) else None
    if active_state is None:
        print("  (no active model — any new model is an improvement)")
        active_acc, active_pc = 0.0, [(c, 0, 0) for c in classes]
    else:
        active_acc, active_pc = eval_model(active_state, VAL_DIR, n, device)
        print(f"  Active val_acc = {active_acc:.2f}%")
        for name, p, r in active_pc:
            print(f"     {name:<12}  P={p:.3f}  R={r:.3f}")

    print(f"\n• Evaluating NEW     : {NEW_PATH}")
    new_state = load_state(NEW_PATH)
    new_acc, new_pc = eval_model(new_state, VAL_DIR, n, device)
    print(f"  New val_acc    = {new_acc:.2f}%")
    for name, p, r in new_pc:
        print(f"     {name:<12}  P={p:.3f}  R={r:.3f}")

    delta = new_acc - active_acc
    print(f"\nΔ = {delta:+.2f}pp")

    if not args.force and delta <= 0:
        print("New model is NOT better than active. Skipping promotion.")
        print("Pass --force to promote anyway.")
        return

    ans = "y" if args.force else input("Promote new model to active? [y/N]: ").strip().lower()
    if ans not in ("y", "yes"):
        print("Aborted.")
        return

    if os.path.isfile(ACTIVE_PATH):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = ACTIVE_PATH.replace(".pth", f".backup_{ts}.pth")
        shutil.copy2(ACTIVE_PATH, backup)
        print(f"✓ Old active backed up → {backup}")
    shutil.copy2(NEW_PATH, ACTIVE_PATH)
    print(f"✓ Promoted {NEW_PATH}  →  {ACTIVE_PATH}")
    print("The app will now use the new model on next request.")


if __name__ == "__main__":
    main()
