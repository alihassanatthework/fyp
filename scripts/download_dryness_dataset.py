"""
scripts/download_dryness_dataset.py
───────────────────────────────────
1. Downloads killa92/facial-skin-analysis-and-type-classification via kagglehub.
2. Re-organises it into a binary dryness layout under
   dataset/efficientnet_b4/dryness/{train,val,test}/{dry,not_dry}/
   using symlinks so no extra disk space is used.

After this script:
   dataset/efficientnet_b4/dryness/
   ├── train/dry/        833 images
   ├── train/not_dry/   2039 images (combination + normal + oily)
   ├── val/dry/          257
   ├── val/not_dry/      555
   ├── test/dry/         113
   └── test/not_dry/     296

Run from the project root:
   python scripts/download_dryness_dataset.py
"""

import os
import shutil
import kagglehub


KAGGLE_HANDLE = "killa92/facial-skin-analysis-and-type-classification"
DST_ROOT      = "dataset/efficientnet_b4/dryness"
SPLIT_MAP     = {"train": "train", "valid": "val", "test": "test"}


def main():
    print(f"⬇  Downloading {KAGGLE_HANDLE} …")
    src_root = kagglehub.dataset_download(KAGGLE_HANDLE)
    print(f"📂 Dataset cached at: {src_root}")

    src_root = os.path.join(src_root, "skin_type_classification_dataset")
    if not os.path.isdir(src_root):
        raise RuntimeError(f"Expected folder not found: {src_root}")

    os.makedirs(DST_ROOT, exist_ok=True)
    total = 0

    for split_src, split_dst in SPLIT_MAP.items():
        for cls in sorted(os.listdir(os.path.join(src_root, split_src))):
            dst_cls = "dry" if cls == "dry" else "not_dry"
            dst_dir = os.path.join(DST_ROOT, split_dst, dst_cls)
            os.makedirs(dst_dir, exist_ok=True)
            for fname in os.listdir(os.path.join(src_root, split_src, cls)):
                src = os.path.join(src_root, split_src, cls, fname)
                # Prefix with original class to avoid name collisions when
                # merging combination/normal/oily into not_dry.
                dst = os.path.join(dst_dir, f"{cls}__{fname}")
                if os.path.exists(dst):
                    continue
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy(src, dst)
                total += 1

    print(f"\n✅ Linked {total} new files.")
    print(f"📁 Layout under {DST_ROOT}/:")
    for split in SPLIT_MAP.values():
        for cls in ["dry", "not_dry"]:
            p = os.path.join(DST_ROOT, split, cls)
            n = len(os.listdir(p)) if os.path.isdir(p) else 0
            print(f"   {split}/{cls:8s}: {n} images")


if __name__ == "__main__":
    main()
