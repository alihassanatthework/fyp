"""
Prepare EfficientNet B4 dataset using ALL available data across sources.

- Merges: current train/val (acne, dark_spots, dryness, normal), dermnet_dataset,
  IMG_CLASSES, acne_dataset.
- Maps source folders to canonical classes (merge duplicates e.g. Eczema → dryness).
- Uses all diseases for maximum accuracy; primary classes: acne, dark_spots, dryness, normal.
- Filters: min images per class, valid image check (skip corrupt).
- Output: dataset/efficientnet_b4_all/train and val (ImageFolder-compatible).

Usage:
  python scripts/prepare_efficientnet_dataset.py
  python scripts/prepare_efficientnet_dataset.py --min-per-class 30 --val-ratio 0.2
"""

import os
import re
import shutil
import random
import argparse
from pathlib import Path
from collections import defaultdict

from PIL import Image

# Paths
BASE = Path(__file__).resolve().parents[1]
DATASET_ROOT = BASE / "dataset" / "efficientnet_b4"
OUT_ROOT = BASE / "dataset" / "efficientnet_b4_all"

EXTENSIONS = (".jpg", ".jpeg", ".png", ".jpe", ".bmp")
TRAIN_SPLIT = 0.8
IMAGE_SIZE = 380  # EfficientNet B4

# Map (source_folder_name_or_pattern) -> canonical class name (lowercase, underscore).
# All images from a folder are assigned to that class. Multiple folders can map to the same class.
# This merges duplicates (e.g. different eczema sources → dryness) and keeps other diseases separate.
FOLDER_TO_CLASS = {
    # ----- Primary classes (acne, dark_spots, dryness, normal) -----
    "acne": "acne",
    "Acne and Rosacea Photos": "acne",
    "Acne": "acne",
    "dark_spots": "dark_spots",
    "Light Diseases and Disorders of Pigmentation": "dark_spots",
    "dryness": "dryness",
    "Eczema Photos": "dryness",
    "Atopic Dermatitis Photos": "dryness",
    "Psoriasis pictures Lichen Planus and related diseases": "dryness",
    "1. Eczema 1677": "dryness",
    "3. Atopic Dermatitis - 1.25k": "dryness",
    "7. Psoriasis pictures Lichen Planus and related diseases - 2k": "dryness",
    "normal": "normal",
    # ----- Other diseases (use all data for max accuracy) -----
    "2. Melanoma 15.75k": "melanoma",
    "Melanoma Skin Cancer Nevi and Moles": "melanoma",
    "4. Basal Cell Carcinoma (BCC) 3323": "basal_cell_carcinoma",
    "Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions": "basal_cell_carcinoma",
    "5. Melanocytic Nevi (NV) - 7970": "melanocytic_nevi",
    "6. Benign Keratosis-like Lesions (BKL) 2624": "benign_keratosis",
    "8. Seborrheic Keratoses and other Benign Tumors - 1.8k": "seborrheic_keratoses",
    "Seborrheic Keratoses and other Benign Tumors": "seborrheic_keratoses",
    "9. Tinea Ringworm Candidiasis and other Fungal Infections - 1.7k": "fungal_infections",
    "Tinea Ringworm Candidiasis and other Fungal Infections": "fungal_infections",
    "Nail Fungus and other Nail Disease": "fungal_infections",
    "10. Warts Molluscum and other Viral Infections - 2103": "viral_infections",
    "Warts Molluscum and other Viral Infections": "viral_infections",
    "Bullous Disease Photos": "bullous_disease",
    "Cellulitis Impetigo and other Bacterial Infections": "bacterial_infections",
    "Poison Ivy Photos and other Contact Dermatitis": "contact_dermatitis",
    "Exanthems and Drug Eruptions": "drug_eruptions",
    "Hair Loss Photos Alopecia and other Hair Diseases": "hair_loss",
    "Herpes HPV and other STDs Photos": "stds_photos",
    "Lupus and other Connective Tissue diseases": "lupus",
    "Scabies Lyme Disease and other Infestations and Bites": "scabies_infestations",
    "Systemic Disease": "systemic_disease",
    "Urticaria Hives": "urticaria",
    "Vascular Tumors": "vascular_tumors",
    "Vasculitis Photos": "vasculitis",
}


def normalize_class_name(folder_name: str) -> str:
    """Map folder name to canonical class; exact match first, then strip numbering for IMG_CLASSES."""
    if folder_name in FOLDER_TO_CLASS:
        return FOLDER_TO_CLASS[folder_name]
    # Strip leading "N. " for IMG_CLASSES-style names and try again
    stripped = re.sub(r"^\d+\.\s*", "", folder_name).strip()
    for key, cls in FOLDER_TO_CLASS.items():
        if key in folder_name or stripped in key:
            return cls
    # Fallback: filesystem-safe name
    safe = re.sub(r"[^\w\s-]", "", folder_name).strip()
    safe = re.sub(r"[-\s]+", "_", safe).lower()
    return safe or "other"


def is_valid_image(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def collect_images_by_class() -> dict[str, list[Path]]:
    """Walk all sources and collect image paths by canonical class."""
    by_class = defaultdict(list)
    sources = [
        DATASET_ROOT / "train",
        DATASET_ROOT / "val",
        DATASET_ROOT / "dermnet_dataset" / "train",
        DATASET_ROOT / "dermnet_dataset" / "test",
        DATASET_ROOT / "IMG_CLASSES",
        DATASET_ROOT / "acne_dataset",
    ]
    for src in sources:
        if not src.is_dir():
            continue
        for root, _, files in os.walk(src):
            root_path = Path(root)
            folder_name = root_path.name
            canonical = normalize_class_name(folder_name)
            for f in files:
                if Path(f).suffix.lower() in EXTENSIONS:
                    by_class[canonical].append(root_path / f)
    return dict(by_class)


def resize_and_copy(img_path: Path, target_path: Path) -> bool:
    try:
        img = Image.open(img_path).convert("RGB")
        img = img.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.LANCZOS)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(target_path, "JPEG", quality=95)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Prepare EfficientNet dataset from all sources.")
    parser.add_argument("--min-per-class", type=int, default=15, help="Drop classes with fewer images")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Validation split ratio")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-validate", action="store_true", help="Skip validating images (faster)")
    args = parser.parse_args()

    random.seed(args.seed)

    print("Collecting images from all sources...")
    by_class = collect_images_by_class()

    # Filter corrupt and small classes
    print("Filtering and validating images...")
    kept = {}
    for cls, paths in by_class.items():
        if args.skip_validate:
            valid_paths = list(paths)
        else:
            valid_paths = [p for p in paths if is_valid_image(p)]
        if len(valid_paths) >= args.min_per_class:
            kept[cls] = valid_paths
        else:
            print(f"  Dropping class '{cls}' (count={len(valid_paths)} < {args.min_per_class})")

    # Sort classes for reproducible order (acne, dark_spots, dryness, normal first, then rest)
    primary = ["acne", "dark_spots", "dryness", "normal"]
    other = sorted(k for k in kept if k not in primary)
    class_order = [c for c in primary if c in kept] + other
    n_classes = len(class_order)
    print(f"Classes to write ({n_classes}): {class_order}")

    # Clean output and create structure
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    (OUT_ROOT / "train").mkdir(parents=True)
    (OUT_ROOT / "val").mkdir(parents=True)

    train_count = val_count = 0
    for cls in class_order:
        paths = kept[cls]
        random.shuffle(paths)
        n_val = max(1, int(len(paths) * args.val_ratio))
        n_train = len(paths) - n_val
        train_paths = paths[:n_train]
        val_paths = paths[n_train:]

        for i, p in enumerate(train_paths):
            ext = Path(p).suffix.lower()
            out = OUT_ROOT / "train" / cls / f"{cls}_{i:05d}{ext}"
            if resize_and_copy(p, out.with_suffix(".jpg")):
                train_count += 1
        for i, p in enumerate(val_paths):
            out = OUT_ROOT / "val" / cls / f"{cls}_{i:05d}.jpg"
            if resize_and_copy(p, out):
                val_count += 1

    print(f"\nDone. Train images: {train_count}, Val images: {val_count}")
    print(f"Output: {OUT_ROOT}")
    print("Run training with: train_dir = 'dataset/efficientnet_b4_all/train', val_dir = 'dataset/efficientnet_b4_all/val'")


if __name__ == "__main__":
    main()
