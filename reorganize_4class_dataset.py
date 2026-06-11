"""
reorganize_4class_dataset.py
────────────────────────────
COPY the disease folders into a clean 4-class structure with disease-level
subfolders, then create an 80/20 stratified train/val split.

HARD RULES (enforced in code):
  • COPY only — never deletes or moves any source file.
  • dataset/efficientnet_b4/dryness/ is on an absolute blocklist; the script
    refuses to read from or write to any path under it.
  • Original filenames preserved (a source-split tag is prefixed ONLY when a
    filename collision would otherwise overwrite another image).

FINAL STRUCTURE (created fresh):
  dataset/acne/{train,val}/<disease_subfolder>/...
  dataset/dryness/{train,val}/<disease_subfolder>/...
  dataset/dark_spots/{train,val}/<disease_subfolder>/...
  dataset/normal/{train,val}/...               (no disease subfolders)

The 80/20 split is stratified at the DISEASE-SUBFOLDER level, which also
guarantees stratification at the top class level.

Usage:
    source venv/bin/activate
    python reorganize_4class_dataset.py            # dry-run: plan + counts only
    python reorganize_4class_dataset.py --apply    # actually copy files
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import time
from collections import defaultdict
from typing import Dict, List

# ── Constants ───────────────────────────────────────────────────────
SEED       = 42
DATA_EXTS  = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
ROOT       = "dataset"
EFF        = "dataset/efficientnet_b4"
DERMNET    = f"{EFF}/dermnet_dataset"
IMG_CLASSES = f"{EFF}/IMG_CLASSES"
VAL_FRAC   = 0.20

# ── Absolute blocklist — never read or write under here ─────────────
BLOCKED = os.path.abspath(f"{EFF}/dryness")

random.seed(SEED)

# ── Source resolution ───────────────────────────────────────────────
# Each target subfolder lists the source folders to pull from. dermnet
# sources merge the train/ and test/ splits. IMG_CLASSES sources are used
# only for the two classes that exist nowhere else.
DERMNET_SPLITS = ["train", "test"]


def dermnet(name: str) -> List[str]:
    return [os.path.join(DERMNET, sp, name) for sp in DERMNET_SPLITS]


def imgcls(name: str) -> List[str]:
    return [os.path.join(IMG_CLASSES, name)]


MAPPING: Dict[str, Dict[str, List[str]]] = {
    "acne": {
        "acne_rosacea":                 dermnet("Acne and Rosacea Photos"),
        "bullous_disease":              dermnet("Bullous Disease Photos"),
        "cellulitis_impetigo_bacterial": dermnet("Cellulitis Impetigo and other Bacterial Infections"),
        "exanthems_drug_eruptions":     dermnet("Exanthems and Drug Eruptions"),
        "herpes_hpv_stds":              dermnet("Herpes HPV and other STDs Photos"),
        "psoriasis_lichen_planus":      dermnet("Psoriasis pictures Lichen Planus and related diseases"),
        "scabies_lyme_infestations":    dermnet("Scabies Lyme Disease and other Infestations and Bites"),
        "tinea_ringworm_fungal":        dermnet("Tinea Ringworm Candidiasis and other Fungal Infections"),
        "urticaria_hives":              dermnet("Urticaria Hives"),
        "warts_molluscum_viral":        dermnet("Warts Molluscum and other Viral Infections"),
    },
    "dryness": {
        "atopic_dermatitis":            dermnet("Atopic Dermatitis Photos"),
        "eczema":                       dermnet("Eczema Photos"),
        "lupus_connective_tissue":      dermnet("Lupus and other Connective Tissue diseases"),
        "nail_fungus_nail_disease":     dermnet("Nail Fungus and other Nail Disease"),
        "poison_ivy_contact_dermatitis": dermnet("Poison Ivy Photos and other Contact Dermatitis"),
        "systemic_disease":             dermnet("Systemic Disease"),
        "vascular_tumors":              dermnet("Vascular Tumors"),
        "vasculitis":                   dermnet("Vasculitis Photos"),
    },
    "dark_spots": {
        "actinic_keratosis_bcc_malignant": dermnet("Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions"),
        "benign_keratosis_like_lesions":   imgcls("6. Benign Keratosis-like Lesions (BKL) 2624"),
        "light_diseases_pigmentation":     dermnet("Light Diseases and Disorders of Pigmentation"),
        "melanocytic_nevi":                imgcls("5. Melanocytic Nevi (NV) - 7970"),
        "melanoma_nevi_moles":             dermnet("Melanoma Skin Cancer Nevi and Moles"),
        "seborrheic_keratoses_benign_tumors": dermnet("Seborrheic Keratoses and other Benign Tumors"),
    },
}

# normal pulls directly from the existing 4-class folders (NOT dryness).
NORMAL_SOURCES = [f"{EFF}/train/normal", f"{EFF}/val/normal"]


# ── Safety helpers ──────────────────────────────────────────────────
def assert_not_blocked(path: str):
    ap = os.path.abspath(path)
    if ap == BLOCKED or ap.startswith(BLOCKED + os.sep):
        raise RuntimeError(f"BLOCKED PATH ACCESS REFUSED: {path}")


def list_images(folder: str) -> List[str]:
    assert_not_blocked(folder)
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(DATA_EXTS)]


# ── Gather phase (no writes) ────────────────────────────────────────
def gather() -> Dict:
    """Return a plan: class → subfolder → list of (src_path, src_tag)."""
    plan = {}
    missing = []
    for cls, subs in MAPPING.items():
        plan[cls] = {}
        for sub, sources in subs.items():
            files = []
            for src in sources:
                imgs = list_images(src)
                if not imgs and not os.path.isdir(src):
                    missing.append(src)
                # tag = parent split (train/test) or 'img' for IMG_CLASSES
                parent = os.path.basename(os.path.dirname(src))
                tag = parent if parent in ("train", "test") else "img"
                files.extend((p, tag) for p in imgs)
            plan[cls][sub] = files

    # normal
    plan["normal"] = {"_root": []}
    for src in NORMAL_SOURCES:
        imgs = list_images(src)
        if not imgs and not os.path.isdir(src):
            missing.append(src)
        tag = os.path.basename(src)  # 'normal' both — use parent split
        split_tag = os.path.basename(os.path.dirname(src))  # train/val
        plan["normal"]["_root"].extend((p, split_tag) for p in imgs)

    return plan, missing


def stratified_split(items: List, val_frac: float):
    """Deterministic 80/20 split of a list."""
    items = list(items)
    rng = random.Random(SEED + len(items))
    rng.shuffle(items)
    n_val = int(round(len(items) * val_frac))
    return items[n_val:], items[:n_val]   # train, val


# ── Apply phase (copies) ────────────────────────────────────────────
def copy_into(dst_dir: str, files: List, counters: dict):
    assert_not_blocked(dst_dir)
    os.makedirs(dst_dir, exist_ok=True)
    seen = set(os.listdir(dst_dir))
    copied = 0
    for src_path, tag in files:
        base = os.path.basename(src_path)
        dst_name = base
        if dst_name in seen:
            # collision — disambiguate with source tag, preserve original name
            stem, ext = os.path.splitext(base)
            dst_name = f"{stem}__{tag}{ext}"
            k = 1
            while dst_name in seen:
                dst_name = f"{stem}__{tag}_{k}{ext}"
                k += 1
        seen.add(dst_name)
        shutil.copy2(src_path, os.path.join(dst_dir, dst_name))
        copied += 1
    counters['files'] += copied
    return copied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='Actually copy files. Without it, dry-run plan only.')
    ap.add_argument('--out', default='dataset',
                    help='Root under which acne/dryness/dark_spots/normal are created.')
    args = ap.parse_args()

    print("🔒 Blocklist (never touched):", BLOCKED)
    print(f"{'🚀 APPLY' if args.apply else '🧪 DRY-RUN'} mode\n")

    t0 = time.time()
    plan, missing = gather()

    # ── Build split assignments + counts ──
    report = {'classes': {}, 'missing_sources': missing}
    grand_train = grand_val = 0
    for cls, subs in plan.items():
        report['classes'][cls] = {'subfolders': {}, 'total': 0,
                                    'train': 0, 'val': 0}
        for sub, files in subs.items():
            tr, va = stratified_split(files, VAL_FRAC)
            report['classes'][cls]['subfolders'][sub] = {
                'total': len(files), 'train': len(tr), 'val': len(va),
            }
            report['classes'][cls]['total'] += len(files)
            report['classes'][cls]['train'] += len(tr)
            report['classes'][cls]['val']   += len(va)
            grand_train += len(tr); grand_val += len(va)

            if args.apply:
                sub_part = '' if sub == '_root' else sub
                copy_into(os.path.join(args.out, cls, 'train', sub_part),
                          tr, _C)
                copy_into(os.path.join(args.out, cls, 'val', sub_part),
                          va, _C)

    # ── Print report ──
    print("══ Per-class / per-subfolder counts ══\n")
    totals = {}
    for cls, info in report['classes'].items():
        print(f"▸ {cls.upper()}  (total {info['total']}  →  "
              f"train {info['train']} / val {info['val']})")
        for sub, c in sorted(info['subfolders'].items()):
            name = '(root)' if sub == '_root' else sub
            print(f"    {name:38s} {c['total']:>6}  "
                  f"(tr {c['train']:>5} / va {c['val']:>4})")
        totals[cls] = info['total']
        print()

    # ── Imbalance ──
    if totals:
        mx, mn = max(totals.values()), max(1, min(totals.values()))
        print("══ Class imbalance (top-level) ══")
        for cls, n in sorted(totals.items(), key=lambda x: -x[1]):
            print(f"    {cls:12s} {n:>7}  ({n/sum(totals.values())*100:5.2f}%)")
        print(f"    imbalance ratio: {mx/mn:.2f}×\n")
        report['imbalance_ratio'] = mx / mn
        report['class_totals'] = totals

    if missing:
        print("⚠ MISSING SOURCE FOLDERS (flagged, skipped):")
        for m in missing:
            print(f"    - {m}")
        print()
    else:
        print("✓ All mapped source folders found.\n")

    report['grand_total_train'] = grand_train
    report['grand_total_val']   = grand_val
    report['val_fraction']      = VAL_FRAC
    report['applied']           = args.apply
    report['elapsed_sec']       = round(time.time() - t0, 1)

    os.makedirs('reorg_4class_report', exist_ok=True)
    with open('reorg_4class_report/reorg_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    if args.apply:
        print(f"✅ COPIED {_C['files']} files into '{args.out}/"
              "{acne,dryness,dark_spots,normal}/{train,val}/'")
    else:
        print(f"🧪 DRY-RUN complete — would create "
              f"{grand_train} train + {grand_val} val files.")
        print("   Re-run with --apply to perform the copy.")
    print(f"📝 reorg_4class_report/reorg_report.json written.")
    print(f"⏱  {report['elapsed_sec']}s")


# global copy counter
_C = {'files': 0}

if __name__ == '__main__':
    main()
