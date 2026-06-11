"""
merge_legacy_folders.py
───────────────────────
Merge the remaining legacy source folders into the consolidated 4-class
structure under dataset/efficientnet_b4/, then delete the emptied sources.

Mapping (visual criteria, consistent with the earlier reorg):
  acne_dataset/Acne                         → acne/train/acne_dataset/
  IMG_CLASSES/1. Eczema                      → dryness_new/train/eczema/
  IMG_CLASSES/3. Atopic Dermatitis           → dryness_new/train/atopic_dermatitis/
  IMG_CLASSES/10. Warts Molluscum Viral      → acne/train/warts_molluscum_viral/
  IMG_CLASSES/7. Psoriasis Lichen Planus     → acne/train/psoriasis_lichen_planus/
  IMG_CLASSES/9. Tinea Ringworm Fungal       → acne/train/tinea_ringworm_fungal/
  IMG_CLASSES/2. Melanoma                    → dark_spots/train/melanoma_nevi_moles/
  IMG_CLASSES/4. Basal Cell Carcinoma        → dark_spots/train/actinic_keratosis_bcc_malignant/
  IMG_CLASSES/8. Seborrheic Keratoses        → dark_spots/train/seborrheic_keratoses_benign_tumors/
  data_eczema/images  (images ONLY, no masks) → dryness_new/train/eczema_segmentation/

After merge: delete acne_dataset/, IMG_CLASSES/, data_eczema/ entirely.

Guards: operates only under dataset/efficientnet_b4/, never touches scalp_yolo,
never touches the consolidated class roots except to add into the named train
subfolders. Original filenames preserved (collision → suffix).
"""

from __future__ import annotations

import json
import os
import shutil
import time
from typing import List

EFF = "dataset/efficientnet_b4"
DATA_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

EFF_ABS = os.path.abspath(EFF)
SCALP = os.path.abspath("dataset/scalp_yolo")

# (source folder, destination subfolder)
MERGES = [
    (f"{EFF}/acne_dataset/Acne",                                            f"{EFF}/acne/train/acne_dataset"),
    (f"{EFF}/IMG_CLASSES/1. Eczema 1677",                                   f"{EFF}/dryness_new/train/eczema"),
    (f"{EFF}/IMG_CLASSES/3. Atopic Dermatitis - 1.25k",                     f"{EFF}/dryness_new/train/atopic_dermatitis"),
    (f"{EFF}/IMG_CLASSES/10. Warts Molluscum and other Viral Infections - 2103", f"{EFF}/acne/train/warts_molluscum_viral"),
    (f"{EFF}/IMG_CLASSES/7. Psoriasis pictures Lichen Planus and related diseases - 2k", f"{EFF}/acne/train/psoriasis_lichen_planus"),
    (f"{EFF}/IMG_CLASSES/9. Tinea Ringworm Candidiasis and other Fungal Infections - 1.7k", f"{EFF}/acne/train/tinea_ringworm_fungal"),
    (f"{EFF}/IMG_CLASSES/2. Melanoma 15.75k",                               f"{EFF}/dark_spots/train/melanoma_nevi_moles"),
    (f"{EFF}/IMG_CLASSES/4. Basal Cell Carcinoma (BCC) 3323",               f"{EFF}/dark_spots/train/actinic_keratosis_bcc_malignant"),
    (f"{EFF}/IMG_CLASSES/8. Seborrheic Keratoses and other Benign Tumors - 1.8k", f"{EFF}/dark_spots/train/seborrheic_keratoses_benign_tumors"),
    # images only — masks excluded
    (f"{EFF}/data_eczema/images",                                          f"{EFF}/dryness_new/train/eczema_segmentation"),
]

DELETE_SOURCES = [
    f"{EFF}/acne_dataset",
    f"{EFF}/IMG_CLASSES",
    f"{EFF}/data_eczema",
]


def guard(path: str):
    ap = os.path.abspath(path)
    if ap.startswith(SCALP):
        raise RuntimeError(f"REFUSED (scalp_yolo): {path}")
    if not ap.startswith(EFF_ABS):
        raise RuntimeError(f"REFUSED (outside efficientnet_b4): {path}")


def images_in(folder: str) -> List[str]:
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(DATA_EXTS)]


def main():
    t0 = time.time()
    report = {'merges': [], 'deleted_sources': []}

    print("══ MERGE ══ legacy folders → consolidated class subfolders\n")
    total_moved = 0
    for src, dst in MERGES:
        guard(src); guard(dst)
        if not os.path.isdir(src):
            print(f"  ⚠ source missing: {src}")
            report['merges'].append({'src': src, 'dst': dst, 'moved': 0,
                                      'status': 'src_missing'})
            continue
        os.makedirs(dst, exist_ok=True)
        seen = set(os.listdir(dst))
        files = images_in(src)
        moved = 0
        for fp in files:
            base = os.path.basename(fp)
            name = base
            if name in seen:
                stem, ext = os.path.splitext(base)
                k = 1
                name = f"{stem}__img{ext}"
                while name in seen:
                    name = f"{stem}__img_{k}{ext}"; k += 1
            seen.add(name)
            shutil.move(fp, os.path.join(dst, name))
            moved += 1
        total_moved += moved
        print(f"  ✓ {moved:>5}  {os.path.basename(src)[:45]:45s} → {os.path.relpath(dst, EFF)}")
        report['merges'].append({'src': src, 'dst': dst, 'moved': moved,
                                  'status': 'ok'})

    print(f"\n  total images moved: {total_moved}")

    print("\n══ DELETE ══ emptied source folders")
    for d in DELETE_SOURCES:
        guard(d)
        if os.path.isdir(d):
            leftover = sum(len(images_in(os.path.join(r)))
                           for r, _, _ in os.walk(d))
            shutil.rmtree(d)
            print(f"  ✓ deleted {d}  (leftover non-merged images: {leftover})")
            report['deleted_sources'].append({'path': d, 'leftover_images': leftover})
        else:
            print(f"  ⚠ not found: {d}")

    # ── Final counts per class ──
    print("\n══ FINAL counts per class ══")
    final = {}
    for cls in ["acne", "dryness_new", "dark_spots", "normal"]:
        cdir = os.path.join(EFF, cls)
        tr = sum(len(images_in(os.path.join(r))) for r, _, _ in os.walk(os.path.join(cdir, 'train')))
        va = sum(len(images_in(os.path.join(r))) for r, _, _ in os.walk(os.path.join(cdir, 'val')))
        final[cls] = {'train': tr, 'val': va, 'total': tr + va}
        print(f"  {cls:12s} train={tr:>6}  val={va:>5}  total={tr+va:>6}")
    report['final_counts'] = final
    report['total_moved'] = total_moved
    report['elapsed_sec'] = round(time.time() - t0, 1)

    os.makedirs('reorg_4class_report', exist_ok=True)
    with open('reorg_4class_report/merge_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Done in {report['elapsed_sec']}s")
    print("📝 reorg_4class_report/merge_report.json")


if __name__ == '__main__':
    main()
