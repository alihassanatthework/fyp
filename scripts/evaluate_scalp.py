"""
evaluate_scalp.py
─────────────────
Phase 3 — evaluate the trained 5-class scalp classifier on the FROZEN test
split (dataset/scalp_clean/test/), which was never used for training or
balancing. This is the honest, leakage-free accuracy estimate.

Reports:
  • Overall + per-class accuracy / precision / recall / F1
  • Full confusion matrix (catches "everything is class X" + grouping confusion)
  • Optional 3-crop TTA (--tta) for a small accuracy bump

Run:
    python scripts/evaluate_scalp.py
    python scripts/evaluate_scalp.py --tta
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from efficientnet_pytorch import EfficientNet
from sklearn.metrics import (classification_report, confusion_matrix,
                             accuracy_score)

WEIGHTS = "core/ai_models/scalp_classifier_v1.pth"
DATA_ROOT = "dataset/scalp_clean"
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def pick_device(name):
    if name == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    if name == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_model(device):
    ckpt = torch.load(WEIGHTS, map_location="cpu", weights_only=False)
    classes = ckpt["classes"]
    img_size = ckpt.get("img_size", 224)
    arch = ckpt.get("arch", "efficientnet-b0")
    model = EfficientNet.from_name(arch, num_classes=len(classes))
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()
    return model, classes, img_size


@torch.no_grad()
def run(model, loader, device, classes, tta):
    ys, ps = [], []
    for x, y in loader:
        x = x.to(device)
        if tta:
            logits = sum(model(t).softmax(1) for t in
                         (x, torch.flip(x, dims=[3]),
                          torch.flip(x, dims=[2]))) / 3.0
        else:
            logits = model(x).softmax(1)
        ps.extend(logits.argmax(1).cpu().tolist())
        ys.extend(y.tolist())
    return np.array(ys), np.array(ps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="mps", choices=["mps", "cuda", "cpu"])
    ap.add_argument("--tta", action="store_true", help="3-view test-time augmentation")
    ap.add_argument("--batch-size", type=int, default=16)
    args = ap.parse_args()

    if not os.path.exists(WEIGHTS):
        raise SystemExit(f"✗ {WEIGHTS} not found — train first: bash scripts/train_scalp.sh")

    device = pick_device(args.device)
    model, classes, img_size = load_model(device)
    print(f"🖥  device={device}  classes={classes}  img={img_size}  tta={args.tta}")

    eval_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    test_ds = datasets.ImageFolder(os.path.join(DATA_ROOT, "test"), transform=eval_tf)
    # Ensure ImageFolder class order matches the checkpoint's
    assert test_ds.classes == classes, (
        f"class mismatch: ckpt={classes} folder={test_ds.classes}")
    loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=4)
    print(f"📦 test images: {len(test_ds)}")

    ys, ps = run(model, loader, device, classes, args.tta)

    acc = accuracy_score(ys, ps)
    print(f"\n🎯 Overall test accuracy: {acc*100:.2f}%\n")
    print("Per-class report:")
    print(classification_report(ys, ps, target_names=classes, digits=3, zero_division=0))

    print("Confusion matrix (rows=true, cols=pred):")
    cm = confusion_matrix(ys, ps)
    head = "true\\pred  " + "  ".join(f"{c[:6]:>6}" for c in classes)
    print(head)
    for i, c in enumerate(classes):
        row = "  ".join(f"{v:>6}" for v in cm[i])
        print(f"{c[:9]:<9}  {row}")

    # Per-class accuracy + sanity check
    print("\nPer-class accuracy:")
    for i, c in enumerate(classes):
        tot = cm[i].sum()
        print(f"  {c:<11} {cm[i, i]/max(1,tot)*100:5.1f}%   ({cm[i, i]}/{tot})")
    worst = min(range(len(classes)), key=lambda i: cm[i, i]/max(1, cm[i].sum()))
    print(f"\n⚠ Weakest class: {classes[worst]} — inspect its confusion row above "
          "if accuracy is low (may indicate sub-condition grouping confusion).")


if __name__ == "__main__":
    main()
