#!/usr/bin/env python3
"""
Prepare a skin dataset (images + masks) into the folder layout expected by the U-Net trainer.

Output layout:
  data/
    train/
      images/
      masks/
    val/
      images/
      masks/

Usage:
  python scripts/prepare_skin_dataset.py --raw /path/to/extracted/kaggle_dataset --out data --val-split 0.2

This script uses heuristics to pair images with masks. If your dataset uses polygon annotations (JSON/COCO),
you'll need a separate rasterization step — I can add that if needed.
"""
from pathlib import Path
import argparse
import shutil
import random
import cv2
import numpy as np

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}


def find_images_and_masks(raw_dir: Path):
    images = []
    masks = []
    for p in raw_dir.rglob('*'):
        if p.suffix.lower() in IMAGE_EXTS:
            name = p.name.lower()
            if 'mask' in name or 'seg' in name or 'label' in name:
                masks.append(p)
            else:
                images.append(p)
    return images, masks


def map_pairs(images, masks):
    # Map by stem names first, else fuzzy contains
    mask_map = {m.stem.lower(): m for m in masks}
    pairs = []
    for img in images:
        stem = img.stem.lower()
        matched = None
        if stem in mask_map:
            matched = mask_map[stem]
        else:
            # try stem + _mask or containing
            for k, m in mask_map.items():
                if k == stem + '_mask' or stem in k or k in stem:
                    matched = m
                    break
        pairs.append((img, matched))
    return pairs


def convert_mask_to_binary(mask_path: Path, out_path: Path, threshold=127):
    img = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(f"Failed to read mask: {mask_path}")
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    _, bin_mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    cv2.imwrite(str(out_path), bin_mask)


def prepare(raw_dir: Path, out_dir: Path, val_split=0.2, seed=42):
    raw_dir = raw_dir.resolve()
    out_dir = out_dir.resolve()
    print("Scanning raw dataset:", raw_dir)
    images, masks = find_images_and_masks(raw_dir)
    print(f"Found {len(images)} images and {len(masks)} masks (candidates)")
    pairs = map_pairs(images, masks)
    # Keep only pairs with masks
    paired = [(i, m) for i, m in pairs if m is not None]
    print(f"Using {len(paired)} image+mask pairs (images without masks will be ignored)")

    random.Random(seed).shuffle(paired)
    n_val = int(len(paired) * val_split)
    val_pairs = paired[:n_val]
    train_pairs = paired[n_val:]

    for split in ['train', 'val']:
        (out_dir / split / 'images').mkdir(parents=True, exist_ok=True)
        (out_dir / split / 'masks').mkdir(parents=True, exist_ok=True)

    def copy_pairs(list_pairs, split_name):
        for img_p, mask_p in list_pairs:
            dst_img = out_dir / split_name / 'images' / img_p.name
            dst_mask = out_dir / split_name / 'masks' / (img_p.stem + '.png')
            shutil.copy2(img_p, dst_img)
            try:
                convert_mask_to_binary(mask_p, dst_mask)
            except Exception as e:
                print('Warning: failed to convert mask', mask_p, e)
                m = cv2.imread(str(mask_p), cv2.IMREAD_GRAYSCALE)
                if m is None:
                    print('Skipping - cannot read mask:', mask_p)
                    continue
                _, bin_mask = cv2.threshold(m, 127, 255, cv2.THRESH_BINARY)
                cv2.imwrite(str(dst_mask), bin_mask)

    copy_pairs(train_pairs, 'train')
    copy_pairs(val_pairs, 'val')
    print('Done. Train:', len(train_pairs), 'Val:', len(val_pairs))
    return out_dir


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--raw', required=True, help='Path to extracted dataset folder')
    p.add_argument('--out', default='data', help='Output base folder')
    p.add_argument('--val-split', type=float, default=0.2)
    args = p.parse_args()
    out = prepare(Path(args.raw), Path(args.out), val_split=args.val_split)
    print('Prepared dataset at:', out)
