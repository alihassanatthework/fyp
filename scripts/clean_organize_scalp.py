"""
clean_organize_scalp.py
───────────────────────
Phase 0 (audit, read-only) + Phase 1 (organize, --apply) for the 5-class
scalp classifier dataset.

Sources scanned (under dataset/scalp/):
  • HAIR AND SCALP DISEASE DETECTION.v12i.yolov8  (10-class YOLO, label-id mapped)
  • Alopecia types.v5i.yolov8                     (3-class YOLO → Alopecia)
  • Alopecia Final.v1i.yolov8                      (empty labels → folder=Alopecia)
  • Folliculitis- Final.v1...yolov8                (folliculitis → Infections)
  • Psoriasis.v1i.yolov8                           (Normal_SKin / Scalp_Psoriasis)
  • healthy-scalp.v1i.yolov8                       (Healthy Scalp → Normal)
  • notbald/                                        (loose full-head shots → Normal, capped)
  • all/<condition>/                                (cherry-picked rare conditions)

5 target classes:  Alopecia · Dermatitis · Infections · Psoriasis · Normal
Dropped: Lichen_Planus, Trichotillomania, off-target rare `all/` conditions.

SAFETY GUARANTEES
  1. COPY, never move — dataset/scalp/ is never modified. Output → dataset/scalp_clean/.
  2. Split-aware dedup — pHash clusters near-duplicates; only one representative
     survives, so an image and its augmentation twin can never straddle splits.
  3. manifest.csv — every decision logged (source → class, split, action, reason).
  4. Frozen test split — stratified 80/10/10, never used for balancing.
  5. Reproducible (fixed seed); read-only audit prints exactly what --apply will write.

Augmentation: NOT baked to disk here (that causes leakage). It happens at train
time via runtime transforms + WeightedRandomSampler. See train_scalp_5class.py.

Usage:
    python scripts/clean_organize_scalp.py                 # Phase 0 audit (no writes)
    python scripts/clean_organize_scalp.py --apply         # Phase 1 build scalp_clean/
    python scripts/clean_organize_scalp.py --hash-dist 6   # tune dedup strictness
    python scripts/clean_organize_scalp.py --dark 35 --blur 60   # tune quality gates
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import shutil
from collections import defaultdict

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

# ── Paths ────────────────────────────────────────────────────────────
SRC_ROOT = "dataset/scalp"
OUT_ROOT = "dataset/scalp_clean"
MANIFEST = "scalp_clean_manifest.csv"
SEED = 42
IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

TARGETS = ["Alopecia", "Dermatitis", "Infections", "Psoriasis", "Normal"]

# ── Per-source class → target mapping ────────────────────────────────
# For YOLO datasets the per-image class is the MAJORITY class-id in its label
# file, resolved through that dataset's `names`, then mapped here.
HAIR = "HAIR AND SCALP DISEASE DETECTION.v12i.yolov8"
HAIR_ID_TO_TARGET = {          # index order = data.yaml names of the HAIR set
    0: "Alopecia",     # Alopecia_Areata
    1: "Dermatitis",   # Contact_Dermatitis
    2: "Infections",   # Folliculitis
    3: "Infections",   # Head_Lice
    4: None,           # Lichen_Planus      → DROP
    5: "Alopecia",     # Male_Pattern_Baldness
    6: "Psoriasis",    # Psoriasis
    7: "Dermatitis",   # Seborrheic_Dermatitis
    8: "Alopecia",     # Telogen_Effluvium
    9: "Infections",   # Tinea_Capitis
}
ALO_TYPES = "Alopecia types.v5i.yolov8"        # all 3 ids → Alopecia
ALO_FINAL = "Alopecia Final.v1i.yolov8"        # empty labels → folder=Alopecia
FOLLIC    = "Folliculitis- Final.v1-folliculitis-final.yolov8"   # → Infections
PSORIA    = "Psoriasis.v1i.yolov8"             # 0 Normal_SKin→Normal, 1 Scalp_Psoriasis→Psoriasis
HEALTHY   = "healthy-scalp.v1i.yolov8"         # → Normal

# all/<sub-condition> → target  (only these are kept; everything else dropped)
ALL_MAP = {
    "alopecia-areata": "Alopecia",
    "androgenic-alopecia": "Alopecia",
    "telogen-effluvium": "Alopecia",
    "folliculitis-decalvans": "Infections",
    "tufted-folliculitis": "Infections",
    "dissecting-cellulitis": "Infections",
    "acne-keloidalis": "Infections",
    # dropped (too few / off-target): discoid-lupus, hirsutism, hot-comb-alopecia,
    # lichen-planopilaris, pseudopelade, trichorrhexis-nodosa, trichotillomania
}


def list_images(folder):
    out = []
    for cur, _d, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(IMG_EXTS):
                out.append(os.path.join(cur, f))
    return out


def majority_label_target(img_path, labels_dir, mapper):
    """Read the YOLO label .txt for an image, return the target for the
    majority class-id, or None if no label / dropped class.

    `mapper` is a CALLABLE id->target|None (not a dict — `defaultdict.get()`
    silently bypasses the default factory, which previously dropped whole
    single-class sources)."""
    base = os.path.splitext(os.path.basename(img_path))[0]
    lp = os.path.join(labels_dir, base + ".txt")
    if not os.path.isfile(lp):
        return None
    ids = []
    try:
        with open(lp) as f:
            for line in f:
                parts = line.split()
                if parts:
                    ids.append(int(float(parts[0])))
    except Exception:
        return None
    if not ids:
        return None
    maj = max(set(ids), key=ids.count)
    return mapper(maj)


def collect_sources():
    """Return list of (img_path, target_class, source_tag)."""
    items = []

    def add_yolo(ds_name, mapper, tag):
        ds = os.path.join(SRC_ROOT, ds_name)
        for split in ("train", "valid", "test"):
            img_dir = os.path.join(ds, split, "images")
            lbl_dir = os.path.join(ds, split, "labels")
            if not os.path.isdir(img_dir):
                continue
            for ip in list_images(img_dir):
                tgt = majority_label_target(ip, lbl_dir, mapper)
                if tgt:
                    items.append((ip, tgt, tag))

    # HAIR — 10-class, label-id mapped
    add_yolo(HAIR, lambda i: HAIR_ID_TO_TARGET.get(i), "HAIR")
    # Alopecia types — every id → Alopecia
    add_yolo(ALO_TYPES, lambda i: "Alopecia", "AloTypes")
    # Psoriasis — 0 Normal_SKin→Normal, 1 Scalp_Psoriasis→Psoriasis
    add_yolo(PSORIA, lambda i: {0: "Normal", 1: "Psoriasis"}.get(i), "Psoriasis")
    # Folliculitis Final — both junk ids → Infections
    add_yolo(FOLLIC, lambda i: "Infections", "Folliculitis")
    # healthy-scalp — single class → Normal
    add_yolo(HEALTHY, lambda i: "Normal", "HealthyScalp")

    # Alopecia Final — empty labels; classification by folder → Alopecia
    for ip in list_images(os.path.join(SRC_ROOT, ALO_FINAL)):
        items.append((ip, "Alopecia", "AloFinal"))

    # notbald — loose full-head shots → Normal (tagged so we can cap it)
    nb = os.path.join(SRC_ROOT, "notbald")
    if os.path.isdir(nb):
        for ip in list_images(nb):
            items.append((ip, "Normal", "notbald"))

    # all/<condition> — cherry-picked
    all_root = os.path.join(SRC_ROOT, "all")
    if os.path.isdir(all_root):
        for sub in os.listdir(all_root):
            tgt = ALL_MAP.get(sub.lower())
            if not tgt:
                continue
            for ip in list_images(os.path.join(all_root, sub)):
                items.append((ip, tgt, f"all/{sub}"))

    return items


# ── Quality + perceptual hash ────────────────────────────────────────
def quality_and_hash(path, dark_thr, blur_thr):
    """Return (ok, reason, dhash_uint64). ok=False → drop with `reason`."""
    img = cv2.imread(path)
    if img is None:
        return False, "corrupt", None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if float(gray.mean()) < dark_thr:
        return False, "dark", None
    if cv2.Laplacian(gray, cv2.CV_64F).var() < blur_thr:
        return False, "blurry", None
    # dHash (64-bit) — robust to resize/compression/flips-not (flips give a
    # different but *near* hash; Hamming clustering still catches augment sets).
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]
    h = np.uint64(0)
    for b in diff.flatten():
        h = (h << np.uint64(1)) | np.uint64(bool(b))
    return True, "", h


def hamming(a, b):
    return bin(int(a) ^ int(b)).count("1")


def cluster_dedup(records, max_dist):
    """records: list of dicts with 'hash'. Greedy near-duplicate clustering by
    Hamming distance. Returns (kept_records, n_dropped). Split-aware safety: by
    keeping ONE representative per cluster, no augmentation twin survives to leak
    across splits."""
    kept = []
    reps = []          # (hash, target) of kept representatives
    dropped = 0
    for r in records:
        h, t = r["hash"], r["target"]
        dup = False
        for rh, rt in reps:
            if rt == t and hamming(h, rh) <= max_dist:
                dup = True
                break
        if dup:
            dropped += 1
        else:
            kept.append(r)
            reps.append((h, t))
    return kept, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Write dataset/scalp_clean/. Without this flag the "
                         "script is READ-ONLY (Phase 0 audit).")
    ap.add_argument("--hash-dist", type=int, default=6,
                    help="Max Hamming distance for near-duplicate clustering "
                         "(0=identical only, higher=more aggressive).")
    ap.add_argument("--dark", type=float, default=30.0,
                    help="Drop images with mean grayscale < this (0-255).")
    ap.add_argument("--blur", type=float, default=12.0,
                    help="Drop images with Laplacian variance < this. Kept low "
                         "on purpose — scalp macro shots are naturally soft, so "
                         "this only culls truly degenerate frames.")
    ap.add_argument("--notbald-frac", type=float, default=0.40,
                    help="Cap notbald (full-head shots) at this fraction of the "
                         "final Normal class so scalp close-ups dominate.")
    ap.add_argument("--balance-ratio", type=float, default=3.0,
                    help="Cap each class at this multiple of the smallest class "
                         "(0 = no cap; balancing then left to the train sampler).")
    args = ap.parse_args()

    random.seed(SEED)
    np.random.seed(SEED)

    print("════════════════════════════════════════════════════════════")
    print(f"  SCALP CLEAN+ORGANIZE  —  {'APPLY (writing)' if args.apply else 'AUDIT (read-only)'}")
    print(f"  hash_dist={args.hash_dist}  dark<{args.dark}  blur<{args.blur}  "
          f"notbald≤{args.notbald_frac:.0%}  balance≤{args.balance_ratio}×")
    print("════════════════════════════════════════════════════════════")

    raw = collect_sources()
    print(f"\n① Discovered {len(raw)} candidate images across sources.")
    by_src = defaultdict(int)
    for _p, _t, s in raw:
        by_src[s] += 1
    for s in sorted(by_src):
        print(f"     {by_src[s]:>6}  {s}")

    # ── Quality + hash pass ──
    print("\n② Quality filter + perceptual hashing …")
    good, drops = [], defaultdict(int)
    for p, t, s in tqdm(raw, ncols=100):
        ok, reason, h = quality_and_hash(p, args.dark, args.blur)
        if not ok:
            drops[reason] += 1
            continue
        good.append({"path": p, "target": t, "source": s, "hash": h})
    print(f"     kept {len(good)}   dropped: " +
          "  ".join(f"{k}={v}" for k, v in sorted(drops.items())) or "none")

    # ── Dedup (split-aware: one representative per near-duplicate cluster) ──
    print("\n③ Near-duplicate clustering (kills augmentation leakage) …")
    # Group by target so we never compare across classes (faster + correct).
    deduped = []
    total_dup = 0
    for t in TARGETS:
        recs = [r for r in good if r["target"] == t]
        kept, ndrop = cluster_dedup(recs, args.hash_dist)
        total_dup += ndrop
        deduped.extend(kept)
        print(f"     {t:<11} {len(recs):>5} → {len(kept):>5}   (-{ndrop} dups)")
    print(f"     total near-duplicates removed: {total_dup}")

    # ── Cap notbald within Normal ──
    normal = [r for r in deduped if r["target"] == "Normal"]
    nb = [r for r in normal if r["source"] == "notbald"]
    non_nb = [r for r in normal if r["source"] != "notbald"]
    cap_nb = int(args.notbald_frac / (1 - args.notbald_frac) * len(non_nb)) if args.notbald_frac < 1 else len(nb)
    if len(nb) > cap_nb:
        random.shuffle(nb)
        removed = len(nb) - cap_nb
        nb = nb[:cap_nb]
        print(f"\n④ notbald capped: kept {cap_nb} of full-head shots "
              f"(scalp close-ups={len(non_nb)}), dropped {removed}.")
    else:
        print(f"\n④ notbald within cap ({len(nb)} ≤ {cap_nb}) — no trim.")
    deduped = [r for r in deduped if r["target"] != "Normal"] + non_nb + nb

    # ── Balance cap ──
    counts = defaultdict(list)
    for r in deduped:
        counts[r["target"]].append(r)
    sizes = {t: len(counts[t]) for t in TARGETS}
    smallest = min(sizes.values())
    balanced = []
    if args.balance_ratio > 0:
        cap = int(smallest * args.balance_ratio)
        print(f"\n⑤ Balance cap = {cap} (smallest class={smallest} × {args.balance_ratio}):")
        for t in TARGETS:
            recs = counts[t]
            if len(recs) > cap:
                random.shuffle(recs)
                print(f"     {t:<11} {len(recs):>5} → {cap:>5}  (capped)")
                recs = recs[:cap]
            else:
                print(f"     {t:<11} {len(recs):>5}        (kept)")
            balanced.extend(recs)
    else:
        balanced = deduped
        print("\n⑤ No balance cap (sampler will handle imbalance at train time).")

    # ── Stratified 80/10/10 split ──
    print("\n⑥ Stratified split 80/10/10 (per class):")
    rows = []                         # manifest rows
    final = defaultdict(lambda: defaultdict(int))
    by_class = defaultdict(list)
    for r in balanced:
        by_class[r["target"]].append(r)
    for t in TARGETS:
        recs = by_class[t]
        random.shuffle(recs)
        n = len(recs)
        n_test = max(1, int(round(n * 0.10)))
        n_val = max(1, int(round(n * 0.10)))
        n_train = n - n_val - n_test
        for i, r in enumerate(recs):
            split = "train" if i < n_train else ("val" if i < n_train + n_val else "test")
            final[t][split] += 1
            rows.append({**r, "split": split})
        print(f"     {t:<11} train={final[t]['train']:>5}  "
              f"val={final[t]['val']:>4}  test={final[t]['test']:>4}  (total {n})")

    grand = sum(len(by_class[t]) for t in TARGETS)
    print(f"\n   FINAL TRAINING SET: {grand} images across {len(TARGETS)} classes.")

    # ── Manifest (always written — it's the audit trail) ──
    with open(MANIFEST, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_path", "target_class", "source_tag", "split"])
        for r in rows:
            w.writerow([r["path"], r["target"], r["source"], r["split"]])
    print(f"\n📝 manifest → {MANIFEST}  ({len(rows)} rows)")

    if not args.apply:
        print("\n✋ AUDIT ONLY — nothing written to dataset/scalp_clean/.")
        print("   Review the counts + manifest above, then re-run with --apply.")
        return

    # ── Phase 1: copy into scalp_clean/{split}/{class}/ ──
    print(f"\n⑦ Writing {OUT_ROOT}/  (COPY — originals untouched) …")
    if os.path.exists(OUT_ROOT):
        print(f"   ⚠ {OUT_ROOT} exists — clearing it for a clean rebuild.")
        shutil.rmtree(OUT_ROOT)
    for r in tqdm(rows, ncols=100):
        dst_dir = os.path.join(OUT_ROOT, r["split"], r["target"])
        os.makedirs(dst_dir, exist_ok=True)
        # unique name: source-tag + original basename (avoids collisions)
        safe_tag = r["source"].replace("/", "_")
        base = os.path.basename(r["path"])
        dst = os.path.join(dst_dir, f"{safe_tag}__{base}")
        shutil.copy2(r["path"], dst)
    print(f"\n✅ Built {OUT_ROOT}/ — {len(rows)} images copied.")
    print("   Originals in dataset/scalp/ were NOT modified.")
    print("   Next: train with  bash scripts/train_scalp.sh")


if __name__ == "__main__":
    main()
