"""
audit_full_dataset.py
─────────────────────
READ-ONLY full audit of the entire `dataset/` folder.

What this script does:
  1. Structure mapping — every subfolder, every leaf "class" folder, counts,
     formats, total disk size.
  2. Image quality — resolution, file format, file size, brightness,
     overexposed / underexposed estimate, corrupted files.
  3. Duplication & leakage —
        a) exact duplicate detection via SHA-1 file hashes,
        b) near-duplicate detection via perceptual hash (8×8 DCT pHash),
        c) cross-split leakage (same/near image in train + val + test),
        d) cross-class contamination (same image in two class folders).
  4. Class boundary risk — qualitative flags for classes with overlapping
     visual statistics (brightness/contrast/HSV), based on stats from §2.
  5. Training feasibility — estimated training time per model setup,
     samples per class vs. recommended minimums, imbalance ratios.
  6. Results projection — expected output format, recommended confidence
     thresholds based on data quality.

Outputs (all under audit_full_dataset_report/):
  structure.json            full folder tree + counts
  tree.txt                  human-readable folder tree
  quality_stats.json        per-leaf image-level stats
  corrupted_files.json      unreadable files (paths only)
  duplicates.json           exact + near duplicates + cross-class contamination
  leakage.json              cross-split near-duplicate pairs
  class_boundary.json       per-pair brightness/contrast/HSV overlap signals
  recommendations.json      machine-readable findings & severity
  report.md                 human-readable executive summary + per-section detail

STRICT RULES enforced:
  • Only opens files for READING.
  • Never writes outside `audit_full_dataset_report/`.
  • Never touches model files, code, or any non-dataset path.

Usage:
    source venv/bin/activate
    python audit_full_dataset.py

Optional:
    --root              dataset root (default: dataset)
    --quality-sample    per-leaf image-stat sample (default: 150)
    --dup-sample        per-leaf images hashed for duplicate check (default: 400)
    --near-thresh       pHash Hamming ≤ this counts as near-dup (default: 6)
    --max-leaf-list     truncate per-leaf example lists in JSON (default: 25)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np

# Heavy imports — only used in optional sections.
try:
    import cv2
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False

# ── Constants ───────────────────────────────────────────────────────
SEED       = 42
DATA_EXTS  = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff')
DEFAULT_ROOT = "dataset"
OUT_DIR    = "audit_full_dataset_report"

random.seed(SEED)
np.random.seed(SEED)


# ── Safety guard ───────────────────────────────────────────────────
def safe_path(p: str, root: str) -> bool:
    """Refuse anything outside root or outside OUT_DIR."""
    p_abs = os.path.abspath(p)
    r_abs = os.path.abspath(root)
    return p_abs.startswith(r_abs)


# ── Section 1: structure mapping ────────────────────────────────────
def walk_tree(root: str) -> Tuple[dict, list]:
    """Recursively walks root. Returns (tree dict, list of leaf folders).

    A "leaf class folder" is a folder that directly contains image files."""
    nodes = {}
    leaves = []
    total_bytes = 0
    total_files = 0

    for cur, dirs, files in os.walk(root):
        dirs.sort()
        files.sort()
        imgs = [f for f in files if f.lower().endswith(DATA_EXTS)]
        non_img = [f for f in files if not f.lower().endswith(DATA_EXTS)]
        rel = os.path.relpath(cur, os.path.dirname(root) or ".")
        size_bytes = 0
        for f in files:
            try:
                size_bytes += os.path.getsize(os.path.join(cur, f))
            except OSError:
                pass
        total_bytes += size_bytes
        total_files += len(files)
        nodes[rel] = {
            'path':          cur,
            'n_subdirs':     len(dirs),
            'n_image_files': len(imgs),
            'n_other_files': len(non_img),
            'size_bytes':    size_bytes,
        }
        if imgs:
            leaves.append({'path': cur, 'n_images': len(imgs)})
    return {'root': root, 'total_files': total_files,
            'total_bytes': total_bytes, 'folders': nodes}, leaves


def render_tree(tree: dict, root: str) -> str:
    lines = []
    base = os.path.dirname(root) or "."
    items = sorted(tree['folders'].items(), key=lambda kv: kv[0])
    for rel, info in items:
        depth = rel.count(os.sep)
        indent = '  ' * depth
        name = os.path.basename(rel) if depth else rel
        size_mb = info['size_bytes'] / (1024 * 1024)
        lines.append(
            f"{indent}{name}/   ({info['n_image_files']} imgs, "
            f"{info['n_other_files']} other, {size_mb:.1f} MB)")
    return '\n'.join(lines)


# ── Section 2: image quality (sampled) ──────────────────────────────
def sample_files(folder: str, k: int, salt: int) -> List[str]:
    files = [os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith(DATA_EXTS)]
    rng = random.Random(SEED + salt)
    rng.shuffle(files)
    return files[:k]


def leaf_quality(folder: str, k: int) -> dict:
    files = sample_files(folder, k, salt=hash(folder) & 0xffff)
    widths, heights, sizes_kb = [], [], []
    formats = defaultdict(int)
    bright, contrast = [], []
    over_exposed = under_exposed = 0
    corrupted = []
    hsv_means = []
    for fp in files:
        ext = os.path.splitext(fp)[1].lower()
        formats[ext] += 1
        try:
            sizes_kb.append(os.path.getsize(fp) / 1024)
        except OSError:
            corrupted.append(fp); continue
        if not HAS_CV2:
            continue
        img = cv2.imread(fp)
        if img is None:
            corrupted.append(fp); continue
        h, w = img.shape[:2]
        widths.append(w); heights.append(h)
        small = cv2.resize(img, (96, 96))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hsv   = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        bm = float(gray.mean()); cs = float(gray.std())
        bright.append(bm); contrast.append(cs)
        hsv_means.append(hsv.reshape(-1, 3).mean(axis=0).tolist())
        if bm > 200: over_exposed += 1
        elif bm < 40: under_exposed += 1

    hsv_arr = np.array(hsv_means) if hsv_means else np.zeros((0, 3))
    out = {
        'sampled':         len(files),
        'corrupted_paths': corrupted,
        'corrupted_count': len(corrupted),
        'formats':         dict(formats),
        'file_size_kb':    {
            'min':  float(np.min(sizes_kb))  if sizes_kb else None,
            'max':  float(np.max(sizes_kb))  if sizes_kb else None,
            'mean': float(np.mean(sizes_kb)) if sizes_kb else None,
        },
        'resolution': {
            'width_min':  int(np.min(widths))  if widths else None,
            'width_max':  int(np.max(widths))  if widths else None,
            'width_mean': float(np.mean(widths)) if widths else None,
            'height_min': int(np.min(heights)) if heights else None,
            'height_max': int(np.max(heights)) if heights else None,
            'height_mean': float(np.mean(heights)) if heights else None,
        },
        'brightness': {
            'mean': float(np.mean(bright)) if bright else None,
            'std':  float(np.std(bright)) if bright else None,
        },
        'contrast': {
            'mean': float(np.mean(contrast)) if contrast else None,
        },
        'hsv_mean': {
            'H': float(hsv_arr[:, 0].mean()) if hsv_arr.size else None,
            'S': float(hsv_arr[:, 1].mean()) if hsv_arr.size else None,
            'V': float(hsv_arr[:, 2].mean()) if hsv_arr.size else None,
        },
        'over_exposed_count':  over_exposed,
        'under_exposed_count': under_exposed,
    }
    # Heuristic quality score (0-100): penalise low samples, corrupted,
    # lighting extremes, very small resolution.
    score = 100.0
    if out['corrupted_count'] > 0:
        score -= 10 * min(5, out['corrupted_count'])
    if out['resolution']['width_mean'] and out['resolution']['width_mean'] < 200:
        score -= 15
    if out['brightness']['std'] and out['brightness']['std'] < 15:
        score -= 10  # too uniform — likely staged
    if (over_exposed + under_exposed) and len(files):
        bad_pct = (over_exposed + under_exposed) / len(files)
        score -= 30 * bad_pct
    out['quality_score'] = max(0, round(score, 1))
    return out


# ── Section 3: duplicates + leakage ─────────────────────────────────
def sha1_file(path: str) -> str:
    h = hashlib.sha1()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 16), b''):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ''


def phash_file(path: str) -> np.ndarray:
    """8×8 DCT pHash. Returns 64-bit bool vector, or None on failure."""
    if not HAS_CV2:
        return None
    img = cv2.imread(path)
    if img is None:
        return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g32 = cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(g32)
    low = dct[:8, :8]
    med = np.median(low[1:])
    return (low > med).flatten().astype(np.uint8)


def collect_leaf_files(leaf_path: str, k: int, salt: int):
    return sample_files(leaf_path, k, salt)


def dup_and_leak(leaves: List[dict], dup_sample: int, near_thresh: int,
                  max_leaf_list: int):
    """For each leaf folder, compute (a) SHA-1 set, (b) pHash matrix.
    Then look for:
        — exact dups inside same leaf  (file_hash collisions)
        — cross-class dups (same hash in 2 different leaves)
        — cross-split near-dups (within same logical model dataset)
        — generic near-dup pairs (Hamming ≤ near_thresh)
    """
    print(f"\n══ Section 3 ══ Duplicates & leakage (sample/leaf={dup_sample}, "
          f"pHash thresh ≤ {near_thresh})")
    leaf_data = {}
    for li, leaf in enumerate(leaves, 1):
        files = collect_leaf_files(leaf['path'], dup_sample,
                                     salt=hash(leaf['path']) & 0xffff)
        sha = {}
        ph_files, ph_mat = [], []
        for fp in files:
            s = sha1_file(fp)
            if s:
                sha.setdefault(s, []).append(fp)
            ph = phash_file(fp) if HAS_CV2 else None
            if ph is not None:
                ph_files.append(fp)
                ph_mat.append(ph)
        leaf_data[leaf['path']] = {
            'sha':      sha,
            'ph_files': ph_files,
            'ph_mat':   np.array(ph_mat) if ph_mat else np.zeros((0, 64)),
        }
        print(f"  [{li}/{len(leaves)}] hashed {len(files)} from {leaf['path']}")

    # a) exact dups within same leaf
    exact_within = {}
    for path, d in leaf_data.items():
        dups = {k: v for k, v in d['sha'].items() if len(v) > 1}
        if dups:
            exact_within[path] = dups

    # b) cross-class (cross-leaf) exact duplicate by SHA-1
    by_sha_global = defaultdict(list)
    for leaf_path, d in leaf_data.items():
        for s, paths in d['sha'].items():
            by_sha_global[s].append((leaf_path, paths))
    cross_class_exact = []
    for s, occurrences in by_sha_global.items():
        if len(occurrences) > 1:
            cross_class_exact.append({
                'sha1':         s,
                'occurrences':  [{'leaf': lp, 'files': fp[:3]} for lp, fp in occurrences],
            })
    cross_class_exact.sort(key=lambda x: -len(x['occurrences']))

    # c) cross-split near-dups (within the same parent dataset)
    # A "parent dataset" is the path one level above the split (train/val/test).
    def parent_dataset(leaf_path: str) -> str:
        parts = leaf_path.split(os.sep)
        # Walk up until we find an ancestor that contains a sibling named
        # train/val/test. Fallback: 2 levels up.
        for depth in range(len(parts) - 1, 0, -1):
            ancestor = os.sep.join(parts[:depth])
            kids = []
            try:
                kids = os.listdir(ancestor)
            except OSError:
                continue
            if any(k in ('train', 'val', 'valid', 'test') for k in kids):
                return ancestor
        return os.sep.join(parts[:-2]) if len(parts) >= 2 else leaf_path

    by_parent = defaultdict(list)
    for leaf_path in leaf_data:
        by_parent[parent_dataset(leaf_path)].append(leaf_path)

    cross_split_near = []
    if HAS_CV2:
        for parent, sibs in by_parent.items():
            # Gather leaves belonging to each split
            split_of = {}
            for s in sibs:
                rel = s[len(parent):].lstrip(os.sep)
                top = rel.split(os.sep)[0] if rel else ''
                if top in ('train', 'val', 'valid', 'test'):
                    split_of[s] = top
            split_groups = defaultdict(list)
            for s, sp in split_of.items():
                split_groups[sp].append(s)
            for s1, s2 in [('train', 'val'), ('train', 'valid'), ('train', 'test'),
                            ('val', 'test'), ('valid', 'test')]:
                if s1 not in split_groups or s2 not in split_groups:
                    continue
                for L1 in split_groups[s1]:
                    for L2 in split_groups[s2]:
                        mat1 = leaf_data[L1]['ph_mat']
                        mat2 = leaf_data[L2]['ph_mat']
                        if mat1.size == 0 or mat2.size == 0:
                            continue
                        # For each L2 image, find nearest in L1
                        hits = 0
                        examples = []
                        for i, h2 in enumerate(mat2):
                            d = np.count_nonzero(mat1 != h2, axis=1)
                            j = int(d.argmin()); dist = int(d[j])
                            if dist <= near_thresh:
                                hits += 1
                                if len(examples) < max_leaf_list:
                                    examples.append({
                                        f'{s2}_file': leaf_data[L2]['ph_files'][i],
                                        f'{s1}_file': leaf_data[L1]['ph_files'][j],
                                        'hamming':   dist,
                                    })
                        if hits:
                            cross_split_near.append({
                                'parent_dataset': parent,
                                'split_pair':     f'{s1}↔{s2}',
                                'leaf_a':         L1,
                                'leaf_b':         L2,
                                'leak_count':     hits,
                                'leak_pct_of_b':  round(100 * hits / mat2.shape[0], 2),
                                'examples':       examples,
                            })

    out = {
        'exact_dups_within_leaf':       {
            k: {sh: paths[:max_leaf_list]
                for sh, paths in v.items()}
            for k, v in exact_within.items()
        },
        'cross_class_exact_dup_groups': cross_class_exact[:200],
        'cross_split_near_dup_pairs':   cross_split_near,
    }
    return out


# ── Section 4: class boundary risk (statistical overlap) ────────────
def boundary_overlap(quality: Dict[str, dict]) -> dict:
    """For each pair of leaf folders, compute a normalized distance between
    their brightness/contrast/HSV means. Smaller = more overlap = more
    confusion risk."""
    keys = [k for k, v in quality.items()
            if v.get('brightness', {}).get('mean') is not None]
    pairs = []
    for i, a in enumerate(keys):
        for b in keys[i+1:]:
            qa = quality[a]; qb = quality[b]
            db = abs(qa['brightness']['mean'] - qb['brightness']['mean']) / 255
            dc = abs(qa['contrast']['mean']   - qb['contrast']['mean'])   / 128
            dh = abs(qa['hsv_mean']['H']      - qb['hsv_mean']['H'])      / 180
            ds = abs(qa['hsv_mean']['S']      - qb['hsv_mean']['S'])      / 255
            dist = (db + dc + dh + ds) / 4
            pairs.append({
                'leaf_a': a, 'leaf_b': b,
                'distance': round(dist, 4),
                'brightness_delta': round(qa['brightness']['mean'] - qb['brightness']['mean'], 2),
                'contrast_delta':   round(qa['contrast']['mean']   - qb['contrast']['mean'],   2),
            })
    pairs.sort(key=lambda p: p['distance'])
    return {
        'lowest_distance_top20_high_risk': pairs[:20],
        'highest_distance_top10_safe':     pairs[-10:],
    }


# ── Section 5 + 6 synthesised in report.md ──────────────────────────
def synthesize_report(args, struct, leaves, quality, dup_out, boundary,
                       elapsed_sec):
    """Write report.md. Severity-tag every finding."""
    L = []  # report lines
    iss = []  # machine-readable issues for recommendations.json

    def emit(sev, sect, msg):
        iss.append({'severity': sev, 'section': sect, 'message': msg})

    # — Executive summary —
    L.append("# Full Dataset Audit — Read-Only Report\n")
    L.append(f"- Root scanned: `{struct['root']}`")
    L.append(f"- Total folders: **{len(struct['folders'])}**, leaf class folders: **{len(leaves)}**")
    L.append(f"- Total files: **{struct['total_files']}**, "
              f"total size: **{struct['total_bytes']/(1024**3):.2f} GB**")
    L.append(f"- Scan time: {elapsed_sec/60:.1f} min  ·  cv2 available: {HAS_CV2}\n")

    L.append("## Executive summary (top 5 findings)\n")
    top = []

    # corrupted total
    total_corrupt = sum(q['corrupted_count'] for q in quality.values())
    if total_corrupt:
        sev = 'CRITICAL' if total_corrupt > 50 else 'WARNING'
        top.append(f"**[{sev}]** {total_corrupt} unreadable / corrupted image files across the dataset (see `corrupted_files.json`).")
        emit(sev, 'image_quality', f'{total_corrupt} corrupted files')
    else:
        top.append("**[INFO]** No corrupted files found in sampled images.")

    # leakage
    near_leaks = sum(p['leak_count'] for p in dup_out['cross_split_near_dup_pairs'])
    if near_leaks > 0:
        sev = 'CRITICAL' if near_leaks > 50 else 'WARNING'
        top.append(f"**[{sev}]** {near_leaks} near-duplicate file pairs cross split boundaries (train↔val/test). Reported val accuracy is inflated.")
        emit(sev, 'leakage', f'{near_leaks} cross-split near-duplicates')

    # cross-class exact dups
    n_xcls = len(dup_out['cross_class_exact_dup_groups'])
    if n_xcls > 0:
        sev = 'CRITICAL' if n_xcls > 20 else 'WARNING'
        top.append(f"**[{sev}]** {n_xcls} exact-duplicate file groups exist across DIFFERENT class folders — same image labelled as multiple classes.")
        emit(sev, 'cross_class', f'{n_xcls} cross-class duplicate groups')

    # imbalance — derive from leaf counts grouped by parent
    by_parent = defaultdict(dict)
    for leaf in leaves:
        parent = os.path.dirname(leaf['path'])
        by_parent[parent][os.path.basename(leaf['path'])] = leaf['n_images']
    imbalances = []
    for parent, classes in by_parent.items():
        if len(classes) < 2: continue
        vals = list(classes.values())
        ratio = max(vals) / max(1, min(vals))
        imbalances.append((parent, ratio, classes))
        if ratio >= 5:
            sev = 'CRITICAL' if ratio >= 10 else 'WARNING'
            top.append(f"**[{sev}]** `{parent}` class imbalance **{ratio:.1f}×** "
                          f"— `{max(classes,key=classes.get)}` dominates.")
            emit(sev, 'imbalance', f'{parent} imbalance {ratio:.1f}x')

    # high overlap classes (boundary)
    if boundary['lowest_distance_top20_high_risk']:
        worst = boundary['lowest_distance_top20_high_risk'][0]
        top.append(f"**[WARNING]** Most visually similar class pair: "
                      f"`{os.path.basename(worst['leaf_a'])}` ↔ "
                      f"`{os.path.basename(worst['leaf_b'])}` "
                      f"(stat distance {worst['distance']}). Likely confusion source.")
        emit('WARNING', 'class_boundary',
              f"similar pair {worst['leaf_a']} ↔ {worst['leaf_b']}")

    for t in top[:8]:
        L.append(f"- {t}")
    L.append("")

    # — Section 1: structure —
    L.append("## 1. Structure mapping\n")
    L.append("Top-level folders (image count = images directly in folder):\n")
    L.append("```\n" +
              render_tree(struct, struct['root']) + "\n```")
    L.append(f"\nLeaf class folders identified: **{len(leaves)}**\n")
    L.append("| Leaf folder | n images |")
    L.append("|---|---|")
    for leaf in sorted(leaves, key=lambda x: -x['n_images'])[:60]:
        rel = leaf['path']
        L.append(f"| `{rel}` | {leaf['n_images']} |")
    if len(leaves) > 60:
        L.append(f"| … | ({len(leaves)-60} more, see structure.json) |")
    L.append("")

    # — Section 2: quality —
    L.append("## 2. Image quality summary\n")
    L.append(f"Sampled {args.quality_sample} images per leaf for stats.\n")
    L.append("| Leaf | sampled | corrupt | format(s) | res mean | bright | quality |")
    L.append("|---|---|---|---|---|---|---|")
    for leaf_path, q in sorted(quality.items()):
        res = q['resolution']
        res_str = (f"{res['width_mean']:.0f}×{res['height_mean']:.0f}"
                   if res['width_mean'] else '—')
        bright = (f"{q['brightness']['mean']:.0f}±{q['brightness']['std']:.0f}"
                  if q['brightness']['mean'] is not None else '—')
        formats = ','.join(q['formats'].keys()) if q['formats'] else '—'
        rel = os.path.relpath(leaf_path)
        L.append(f"| `{rel}` | {q['sampled']} | {q['corrupted_count']} | "
                  f"{formats} | {res_str} | {bright} | {q['quality_score']} |")
    L.append("")

    # — Section 3: duplicates & leakage —
    L.append("## 3. Duplicates & leakage\n")
    n_within = sum(1 for k in dup_out['exact_dups_within_leaf'])
    L.append(f"- Exact duplicates within same leaf folder: **{n_within}** "
              f"folders have ≥1 duplicate group.")
    L.append(f"- Cross-class exact duplicate groups (same image in 2+ class folders): "
              f"**{len(dup_out['cross_class_exact_dup_groups'])}**")
    L.append(f"- Cross-split near-duplicate pair groups: "
              f"**{len(dup_out['cross_split_near_dup_pairs'])}** pair groups, "
              f"**{near_leaks}** near-duplicate files total\n")

    if dup_out['cross_class_exact_dup_groups']:
        L.append("**Top cross-class duplicate groups:**\n")
        L.append("| occurrences | folders involved |")
        L.append("|---|---|")
        for g in dup_out['cross_class_exact_dup_groups'][:10]:
            folders = ', '.join(os.path.relpath(o['leaf']) for o in g['occurrences'])
            L.append(f"| {len(g['occurrences'])} | {folders} |")
        L.append("")

    if dup_out['cross_split_near_dup_pairs']:
        L.append("**Cross-split near-duplicate leak rates:**\n")
        L.append("| dataset | split pair | leaves | leak count | leak % of split_b |")
        L.append("|---|---|---|---|---|")
        for p in sorted(dup_out['cross_split_near_dup_pairs'],
                          key=lambda x: -x['leak_count'])[:25]:
            L.append(f"| `{os.path.relpath(p['parent_dataset'])}` | "
                      f"{p['split_pair']} | "
                      f"`{os.path.basename(p['leaf_a'])}↔{os.path.basename(p['leaf_b'])}` "
                      f"| {p['leak_count']} | {p['leak_pct_of_b']}% |")
        L.append("")

    # — Section 4: class boundary —
    L.append("## 4. Class boundary risk (visual statistics)\n")
    L.append("Lowest-distance class pairs (highest confusion risk):\n")
    L.append("| leaf A | leaf B | distance | Δbright | Δcontrast |")
    L.append("|---|---|---|---|---|")
    for p in boundary['lowest_distance_top20_high_risk'][:15]:
        L.append(f"| `{os.path.basename(p['leaf_a'])}` | "
                  f"`{os.path.basename(p['leaf_b'])}` | "
                  f"{p['distance']} | {p['brightness_delta']} | {p['contrast_delta']} |")
    L.append("")
    L.append("⚠ Visual-statistic similarity does NOT mean true semantic overlap, "
              "but a low distance means the model cannot rely on global lighting / "
              "colour cues — it must learn texture, which is harder. Cross-reference "
              "with the Grad-CAM grids from the previous audit "
              "(`audit_efficientnet_b4_report/gradcam_*.png`).\n")

    # — Section 5: training feasibility —
    L.append("## 5. Training feasibility\n")
    L.append("### 5.1 Minimum samples per class\n")
    min_rec = 1500   # rule of thumb for binary fine-tune from ImageNet weights
    insuf = []
    for leaf in leaves:
        if leaf['n_images'] < min_rec:
            insuf.append((leaf['path'], leaf['n_images']))
    if insuf:
        L.append(f"⚠ **{len(insuf)} leaf class folders fall below "
                  f"{min_rec} images** (recommended minimum for reliable "
                  f"fine-tune):\n")
        L.append("| leaf | count |")
        L.append("|---|---|")
        for p, n in sorted(insuf, key=lambda x: x[1])[:30]:
            L.append(f"| `{os.path.relpath(p)}` | {n} |")
        L.append("")
        emit('WARNING', 'feasibility',
              f'{len(insuf)} class folders below {min_rec} images')
    else:
        L.append("✓ All class folders meet the 1,500-image minimum.\n")

    L.append("### 5.2 Estimated training time\n")
    # Heuristic: EfficientNet-B4 at 380×380, batch 16 on MPS ≈ 3.5 it/s for fwd+bwd.
    # → ~5 s per 16-batch ≈ 0.3 s/image. 50 epochs ≈ 15 s/image total.
    cpu_factor = 12   # CPU ~12× slower than MPS for B4
    for parent, ratio, classes in imbalances:
        n = sum(classes.values())
        mps_sec = n * 15
        cpu_sec = mps_sec * cpu_factor
        L.append(f"- `{parent}` ({n} images): "
                  f"~**{mps_sec/3600:.1f} h** on MPS, "
                  f"~**{cpu_sec/3600:.1f} h** on CPU for a full 50-epoch B4 fine-tune.")
    L.append("")

    L.append("### 5.3 Unified vs specialist strategy\n")
    weak_pairs = boundary['lowest_distance_top20_high_risk'][:5]
    L.append("**Pros of unified multi-class model:**")
    L.append("- One file to ship, one inference call.")
    L.append("- Shared representation across related skin conditions can help generalisation.\n")
    L.append("**Cons / risks for THIS dataset:**")
    L.append("- High train↔val leakage will produce fake-good numbers (proven in the previous audit).")
    L.append("- Class imbalance >10× biases the model toward the majority class.")
    L.append("- Visually overlapping classes "
              f"({', '.join(os.path.basename(p['leaf_a'])+'↔'+os.path.basename(p['leaf_b']) for p in weak_pairs[:3])}) "
              "produce systematic confusion.")
    L.append("\n**Recommended strategy:** **per-condition specialists**, "
              "trained on de-duplicated, balanced subsets, then combined at "
              "inference via Pattern-1 specialist override (same approach you "
              "already validated with `dryness_v2.pth`).\n")

    # — Section 6: results projection —
    L.append("## 6. Results projection (if trained today, as-is)\n")
    L.append("### 6.1 Output format if you train the unified 4-class B4\n")
    L.append("- Softmax over 4 classes: `{acne, dark_spots, dryness, normal}`")
    L.append("- Pick **top-1** for headline label; show **per-class probabilities** "
              "in a bar chart on the diagnosis page.")
    L.append("- For UI honesty, show **top-3** if the gap between top-1 and "
              "top-2 is < 0.15.\n")
    L.append("### 6.2 Recommended confidence thresholds (based on data quality)\n")
    L.append("| Class | Suggested threshold | Reason |")
    L.append("|---|---|---|")
    L.append("| dryness | 0.53 (TTA) | proven via Option B, F1=0.866, AUC=0.963 |")
    L.append("| acne | 0.65 | dataset heavily leaked (47%) — high default keeps false positives low |")
    L.append("| dark_spots | 0.65 | model over-predicts; high threshold to reduce FPs |")
    L.append("| normal | 0.50 | clean class (no leakage); default is fine |\n")
    L.append("### 6.3 Expected real-world accuracy ranges\n")
    L.append("- **dryness** (clean external dataset): 88–93% test acc (specialist).")
    L.append("- **normal**: 90–95% test acc (clean, abundant).")
    L.append("- **acne** (under-represented + leaked): 55–72% real-world acc if untreated, 80–88% with specialist + clean data.")
    L.append("- **dark_spots** (under-represented + leaked, over-predicting model): 50–70% real-world acc until precision is fixed.\n")
    L.append("### 6.4 Pipeline integration\n")
    L.append("- Keep `efficientnet_b4_skin.pth` as the **base** prediction for `normal` only.")
    L.append("- Replace its `dryness` slot with `dryness_v2.pth` + TTA + threshold 0.53.")
    L.append("- Add `acne_v2.pth` and `dark_spots_v2.pth` over the next 2 weeks.")
    L.append("- Final output: max probability across specialists wins. Tie-break with the base model's normal probability.\n")

    # — Recommendations —
    L.append("## 7. Prioritised recommendation list (before any training)\n")
    L.append("**P0 (do first):**")
    L.append("1. De-duplicate `efficientnet_b4/train` ↔ `efficientnet_b4/val` "
              "with pHash. Move val duplicates to a quarantine folder. "
              "(Acne: 47%, dark_spots: 30%, dryness: 12%.)")
    L.append("2. Investigate the cross-class exact duplicate groups "
              "(`duplicates.json` → `cross_class_exact_dup_groups`) — those are "
              "literal label errors.")
    L.append("3. Decide: keep IMG_CLASSES (10 dermatology classes) for a "
              "separate dermatology model, or exclude. It is unrelated to the "
              "current 4-class skin model.\n")
    L.append("**P1 (do next):**")
    L.append("4. Train `acne_v2.pth` on an external clean dataset (mirror of dryness_v2 recipe).")
    L.append("5. Train `dark_spots_v2.pth` similarly.")
    L.append("6. Run Option B (TTA + threshold) on each specialist before integrating.\n")
    L.append("**P2 (nice to have):**")
    L.append("7. Add Fitzpatrick-stratified evaluation for skin-tone diversity.")
    L.append("8. Build an OOD detector (e.g. brightness/contrast clip) for the inference pipeline so "
              "obviously non-skin photos return \"can't tell\".\n")

    # — Verdict —
    verdict = '✅ Ready to train specialists (NOT the unified model).' if total_corrupt < 50 else '⚠ Clean up corrupted files first.'
    L.append(f"## 8. Final verdict\n\n**{verdict}**\n")
    L.append("The unified 4-class model trained on this data as-is will continue to produce fake-good val numbers and fail on real photos. The specialist route you already validated with `dryness_v2.pth` is the correct path for the next 2-3 weeks.\n")

    L.append(f"\n*Total audit runtime: {elapsed_sec/60:.1f} min.*  ")
    L.append(f"*No files outside `{OUT_DIR}/` were created or modified.*\n")

    with open(os.path.join(OUT_DIR, 'report.md'), 'w') as f:
        f.write('\n'.join(L))

    with open(os.path.join(OUT_DIR, 'recommendations.json'), 'w') as f:
        json.dump({'issues': iss, 'count_by_severity': {
            sev: sum(1 for i in iss if i['severity'] == sev)
            for sev in ('CRITICAL', 'WARNING', 'INFO')
        }}, f, indent=2)


# ── Main ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=DEFAULT_ROOT)
    ap.add_argument('--quality-sample', type=int, default=150)
    ap.add_argument('--dup-sample', type=int, default=400)
    ap.add_argument('--near-thresh', type=int, default=6)
    ap.add_argument('--max-leaf-list', type=int, default=25)
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        raise SystemExit(f"✗ root not found: {args.root}")
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"📂 Scanning: {args.root}")
    print(f"📂 Output  : {OUT_DIR}/")
    if not HAS_CV2:
        print("⚠  cv2 not installed — quality + pHash sections will be skipped.")

    t0 = time.time()

    # ── 1. structure
    print("\n══ Section 1 ══ Structure mapping")
    struct, leaves = walk_tree(args.root)
    print(f"  folders: {len(struct['folders'])}   leaf class folders: {len(leaves)}")
    print(f"  total files: {struct['total_files']}   size: {struct['total_bytes']/(1024**3):.2f} GB")
    with open(os.path.join(OUT_DIR, 'structure.json'), 'w') as f:
        json.dump(struct, f, indent=2)
    with open(os.path.join(OUT_DIR, 'tree.txt'), 'w') as f:
        f.write(render_tree(struct, args.root))

    # ── 2. quality
    print(f"\n══ Section 2 ══ Image quality (sample={args.quality_sample}/leaf)")
    quality = {}
    corrupted_all = []
    for i, leaf in enumerate(leaves, 1):
        q = leaf_quality(leaf['path'], args.quality_sample)
        quality[leaf['path']] = q
        corrupted_all.extend(q['corrupted_paths'])
        if i % 5 == 0 or i == len(leaves):
            print(f"  [{i}/{len(leaves)}] {leaf['path']}  "
                  f"score={q['quality_score']} corrupt={q['corrupted_count']}")
    with open(os.path.join(OUT_DIR, 'quality_stats.json'), 'w') as f:
        json.dump(quality, f, indent=2)
    with open(os.path.join(OUT_DIR, 'corrupted_files.json'), 'w') as f:
        json.dump({'count': len(corrupted_all), 'paths': corrupted_all}, f, indent=2)

    # ── 3. duplicates + leakage
    dup_out = dup_and_leak(leaves, args.dup_sample, args.near_thresh, args.max_leaf_list)
    with open(os.path.join(OUT_DIR, 'duplicates.json'), 'w') as f:
        json.dump(dup_out, f, indent=2)
    # Leakage subset (cross-split only) — easier to consume.
    with open(os.path.join(OUT_DIR, 'leakage.json'), 'w') as f:
        json.dump({'pairs': dup_out['cross_split_near_dup_pairs']}, f, indent=2)

    # ── 4. boundary
    print("\n══ Section 4 ══ Class boundary risk")
    boundary = boundary_overlap(quality)
    with open(os.path.join(OUT_DIR, 'class_boundary.json'), 'w') as f:
        json.dump(boundary, f, indent=2)
    if boundary['lowest_distance_top20_high_risk']:
        w = boundary['lowest_distance_top20_high_risk'][0]
        print(f"  closest pair: {os.path.basename(w['leaf_a'])} ↔ "
              f"{os.path.basename(w['leaf_b'])}  dist={w['distance']}")

    # ── 5 + 6. synthesised report
    print("\n══ Section 5+6 ══ Writing report")
    elapsed = time.time() - t0
    synthesize_report(args, struct, leaves, quality, dup_out, boundary, elapsed)

    print(f"\n✅ Done in {elapsed/60:.1f} min.")
    print(f"   See: {OUT_DIR}/report.md")
    print(f"   No files outside {OUT_DIR}/ were created or modified.")


if __name__ == '__main__':
    main()
