"""
Train EfficientNet-B4 for skin conditions (acne, dark_spots, dryness, normal).

- Resumes from existing .pth if found (core/ai_models or models/).
- Uses MPS on Mac M1 when available; 8GB-RAM safe (small batch, num_workers=0).
- Saves best model to core/ai_models/efficientnet_b4_skin.pth (used by the app).
"""

import os
import sys
import argparse
import torch
import torch.nn as nn
import torch.optim as optim

from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from efficientnet_pytorch import EfficientNet
from tqdm import tqdm

# -------------------------
# CONFIG (8GB Mac M1 safe)
# -------------------------

TRAIN_DIR = "dataset/efficientnet_b4/train"
VAL_DIR = "dataset/efficientnet_b4/val"
# Existing weights (app loads from core/ai_models)
RESUME_PATHS = [
    "core/ai_models/efficientnet_b4_skin.pth",
    "models/efficientnet_b4_skin.pth",
]
OUTPUT_PATH = "core/ai_models/efficientnet_b4_skin.pth"

# Device: MPS (Mac M1) > CUDA > CPU
if torch.backends.mps.is_available():
    DEFAULT_DEVICE = "mps"
elif torch.cuda.is_available():
    DEFAULT_DEVICE = "cuda"
else:
    DEFAULT_DEVICE = "cpu"

# 8GB RAM: keep batch size small
DEFAULT_BATCH_SIZE = 2
DEFAULT_EPOCHS = 30
DEFAULT_LR = 5e-5  # smaller LR when resuming


def get_device(name: str):
    if name == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    if name == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# -------------------------
# DATA TRANSFORMS
# -------------------------

train_transform = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def find_resume_checkpoint():
    for p in RESUME_PATHS:
        if os.path.isfile(p):
            return p
    return None


def main():
    parser = argparse.ArgumentParser(description="Train EfficientNet-B4 (resume from existing .pth, MPS-friendly)")
    parser.add_argument("--train-dir", default=TRAIN_DIR, help="Train dataset root")
    parser.add_argument("--val-dir", default=VAL_DIR, help="Val dataset root")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from existing .pth (default: True)")
    parser.add_argument("--no-resume", action="store_false", dest="resume", help="Train from ImageNet only (ignore existing .pth)")
    parser.add_argument("--resume-path", type=str, default=None, help="Explicit path to .pth to resume from")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Batch size (8GB RAM: use 2)")
    parser.add_argument("--lr", type=float, default=DEFAULT_LR, help="Learning rate")
    parser.add_argument("--device", type=str, default=DEFAULT_DEVICE, choices=("mps", "cuda", "cpu"), help="Device (mps for Mac M1)")
    parser.add_argument("--out", type=str, default=OUTPUT_PATH, help="Path to save best model (app uses core/ai_models/efficientnet_b4_skin.pth)")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()

    device = get_device(args.device)
    print("Using device:", device)
    if device.type == "cpu" and args.device == "mps":
        print("(MPS was requested but not available; using CPU. Install PyTorch with MPS support.)")

    # ---------- Step 1: Dataset ----------
    if not os.path.isdir(args.train_dir) or not os.path.isdir(args.val_dir):
        print(f"ERROR: Train or val dir missing. Train: {args.train_dir}, Val: {args.val_dir}")
        sys.exit(1)

    train_dataset = datasets.ImageFolder(args.train_dir, transform=train_transform)
    val_dataset = datasets.ImageFolder(args.val_dir, transform=val_transform)
    class_names = train_dataset.classes
    num_classes = len(class_names)
    print("Classes:", class_names, "| num_classes:", num_classes)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=False,
    )

    # ---------- Step 2: Model (ImageNet pretrained + your head) ----------
    model = EfficientNet.from_pretrained("efficientnet-b4")
    model._fc = nn.Linear(model._fc.in_features, num_classes)
    model = model.to(device)

    resume_path = args.resume_path or (find_resume_checkpoint() if args.resume else None)
    if resume_path:
        print(f"Resuming from: {resume_path}")
        try:
            ckpt = torch.load(resume_path, map_location=device)
            if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
                state = ckpt["model_state_dict"]
            else:
                state = ckpt
            # Allow loading if head size matches (same num_classes)
            model.load_state_dict(state, strict=True)
            print("Loaded existing weights successfully.")
        except Exception as e:
            print("Could not load checkpoint (will train from ImageNet only):", e)
    else:
        if args.resume:
            print("No existing .pth found; training from ImageNet pretrained only.")

    class_counts = [0]*num_classes
    for _, label in train_dataset.samples:
        class_counts[label] += 1

    weights = [sum(class_counts)/(c if c > 0 else 1) for c in class_counts]

    class_weights = torch.tensor(weights).to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)

    # ---------- Step 3: Confirm before training ----------
    print("\n--- Training config ---")
    print(f"  Epochs: {args.epochs}  Batch size: {args.batch_size}  LR: {args.lr}")
    print(f"  Save best to: {args.out}")
    if not args.yes:
        reply = input("Proceed with training? [y/N]: ").strip().lower()
        if reply != "y" and reply != "yes":
            print("Aborted.")
            sys.exit(0)

    # ---------- Train loop ----------
    best_acc = 0.0
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch + 1}/{args.epochs}")

        model.train()
        train_loss = 0.0
        correct = 0
        total = 0

        for images, labels in tqdm(train_loader, desc="Train"):
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        train_acc = 100.0 * correct / total
        print("Train loss: %.4f  Train acc: %.2f%%" % (train_loss / len(train_loader), train_acc))

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                outputs = model(images)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()

        val_acc = 100.0 * correct / total
        print("Val acc: %.2f%%" % val_acc)

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), args.out)
            print("Best model saved to", args.out)

    print("\nTraining finished. Best val acc: %.2f%%" % best_acc)


if __name__ == "__main__":
    main()
