"""
compare_dryness_models.py
─────────────────────────
Read-only comparison of two existing checkpoints on the held-out dryness
test set. NEITHER model is modified. NO pipeline code is touched.

Models compared:
  1. dryness_v2.pth                — new binary (dry / not_dry)
  2. efficientnet_b4_skin.pth      — original 4-class (acne, dark_spots,
                                     dryness, normal). For comparison we
                                     binarise: "dry" iff dryness class
                                     wins, else "not_dry".

Test set:
  dataset/efficientnet_b4/dryness/test/
    dry/        113 images  (positive class, label 0)
    not_dry/    296 images  (negative class, label 1)

Per request, both models are evaluated INDEPENDENTLY — no ensembling.

Output: side-by-side table with accuracy / precision / recall / F1
(positive=dry), macro metrics, confusion matrices, and average dryness
confidence per model. Plus a verdict and the decision-rule branch.

Run from project root:
    python compare_dryness_models.py
"""

from __future__ import annotations

import os
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, confusion_matrix,
    classification_report, roc_auc_score,
)
from torch.utils.data import DataLoader
from torchvision import datasets, transforms


# ── Paths ──────────────────────────────────────────────────────────
TEST_DIR    = "dataset/efficientnet_b4/dryness/test"
# Accept either name (spec wrote "dryness.pth", actual file is v2).
NEW_PATHS   = ["core/ai_models/dryness.pth",
               "core/ai_models/dryness_v2.pth"]
OLD_PATH    = "core/ai_models/efficientnet_b4_skin.pth"

DEFAULT_OLD_CLASSES = ['acne', 'dark_spots', 'dryness', 'normal']  # alphabetical
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD  = (0.229, 0.224, 0.225)


def pick_device():
    if torch.backends.mps.is_available():
        return torch.device('mps')
    if torch.cuda.is_available():
        return torch.device('cuda')
    return torch.device('cpu')


# ── Architecture loaders ───────────────────────────────────────────
def detect_arch(state_dict):
    """Return 'torchvision' or 'efficientnet_pytorch' based on key names."""
    k = next(iter(state_dict.keys()))
    if k.startswith('features.') or k.startswith('classifier.'):
        return 'torchvision'
    if k.startswith('_') or '_blocks' in k or '_fc' in k:
        return 'efficientnet_pytorch'
    return 'torchvision'  # safe default


def infer_num_classes(state_dict, arch):
    """Look at the last linear layer's output dim."""
    if arch == 'torchvision':
        for key in reversed(list(state_dict.keys())):
            if key.endswith('.weight') and state_dict[key].dim() == 2:
                return state_dict[key].shape[0]
    else:  # efficientnet_pytorch
        if '_fc.weight' in state_dict:
            return state_dict['_fc.weight'].shape[0]
    return 4  # fallback


def load_torchvision_b4(num_classes, state_dict):
    from torchvision.models import efficientnet_b4
    model = efficientnet_b4(weights=None)
    in_feat = model.classifier[1].in_features
    # Two-block classifier path (our new model)
    has_dropout_then_linear = any('classifier.0' in k for k in state_dict.keys())
    if has_dropout_then_linear:
        model.classifier = torch.nn.Sequential(
            torch.nn.Dropout(0.4),
            torch.nn.Linear(in_feat, num_classes),
        )
    else:
        # Single Linear head (the way the original trainer may have used it).
        model.classifier[1] = torch.nn.Linear(in_feat, num_classes)
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing:
        print(f"   ⚠ missing keys:    {len(missing)} (first: {missing[0] if missing else ''})")
    if unexpected:
        print(f"   ⚠ unexpected keys: {len(unexpected)} (first: {unexpected[0] if unexpected else ''})")
    return model


def load_efficientnet_pytorch_b4(num_classes, state_dict):
    try:
        from efficientnet_pytorch import EfficientNet
    except ImportError:
        print("✗ efficientnet_pytorch not installed. "
              "Try: pip install efficientnet_pytorch", file=sys.stderr)
        sys.exit(1)
    model = EfficientNet.from_name('efficientnet-b4', num_classes=num_classes)
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing:
        print(f"   ⚠ missing keys:    {len(missing)} (first: {missing[0] if missing else ''})")
    if unexpected:
        print(f"   ⚠ unexpected keys: {len(unexpected)} (first: {unexpected[0] if unexpected else ''})")
    return model


def load_checkpoint(path, label):
    print(f"\n── Loading {label} ──")
    print(f"   file: {path}")
    ckpt = torch.load(path, map_location='cpu', weights_only=False)
    if isinstance(ckpt, dict) and 'state_dict' in ckpt:
        state = ckpt['state_dict']
        meta  = {k: v for k, v in ckpt.items() if k != 'state_dict'}
    elif isinstance(ckpt, OrderedDict):
        state = ckpt
        meta  = {}
    else:
        state = ckpt
        meta  = {}
    arch = detect_arch(state)
    n_classes = infer_num_classes(state, arch)
    classes = meta.get('classes')
    img_size = meta.get('img_size', 224 if n_classes == 2 else 224)
    mean = tuple(meta.get('normalize_mean', IMAGENET_MEAN))
    std  = tuple(meta.get('normalize_std',  IMAGENET_STD))

    print(f"   arch     : {arch}")
    print(f"   classes  : {classes if classes else '(not embedded — using defaults)'}")
    print(f"   n_classes: {n_classes}")
    print(f"   img_size : {img_size}")

    if arch == 'torchvision':
        model = load_torchvision_b4(n_classes, state)
    else:
        model = load_efficientnet_pytorch_b4(n_classes, state)

    if classes is None:
        if n_classes == 4:
            classes = DEFAULT_OLD_CLASSES
        elif n_classes == 2:
            classes = ['dry', 'not_dry']
        else:
            classes = [f'class_{i}' for i in range(n_classes)]
        print(f"   → assumed classes: {classes}")

    return model, classes, img_size, mean, std


# ── Evaluation ─────────────────────────────────────────────────────
def make_loader(img_size, mean, std, batch_size=32):
    tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])
    ds = datasets.ImageFolder(TEST_DIR, transform=tf)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=0)
    return ds, loader


def evaluate(model, loader, device, classes, dryness_idx, model_name):
    """
    Returns:
        preds:        binary preds (0=dry, 1=not_dry) in test-set encoding
        labels:       true labels (0=dry, 1=not_dry)
        dryness_conf: softmax prob for dryness class per image
    """
    model.eval().to(device)
    all_preds, all_labels, all_conf = [], [], []
    print(f"\n── Evaluating {model_name} on test set ──")
    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs  = torch.softmax(logits, dim=1)
            # Confidence in *dryness*, regardless of model's class index.
            dryness_conf = probs[:, dryness_idx]
            # Did the dryness class win?  → predict label 0 (dry).
            pred_class   = logits.argmax(dim=1)
            pred_label   = (pred_class != dryness_idx).long()   # 0 if dry won, 1 otherwise
            all_preds.extend(pred_label.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
            all_conf.extend(dryness_conf.cpu().tolist())
    return np.array(all_preds), np.array(all_labels), np.array(all_conf)


def compute_metrics(labels, preds, conf):
    acc = accuracy_score(labels, preds)
    p_dry, r_dry, f_dry, _ = precision_recall_fscore_support(
        labels, preds, average='binary', pos_label=0, zero_division=0,
    )
    p_m, r_m, f_m, _ = precision_recall_fscore_support(
        labels, preds, average='macro', zero_division=0,
    )
    cm = confusion_matrix(labels, preds)
    # AUC on dryness-confidence score (positive class is dry = label 0).
    try:
        auc = roc_auc_score((labels == 0).astype(int), conf)
    except Exception:
        auc = float('nan')
    dry_mask = preds == 0
    return {
        'accuracy':            acc,
        'precision_dry':       p_dry,
        'recall_dry':          r_dry,
        'f1_dry':              f_dry,
        'precision_macro':     p_m,
        'recall_macro':        r_m,
        'f1_macro':            f_m,
        'auc_dryness':         auc,
        'confusion_matrix':    cm,
        'mean_conf_overall':   float(conf.mean()),
        'mean_conf_when_pred_dry': float(conf[dry_mask].mean()) if dry_mask.any() else 0.0,
        'n_total':             len(labels),
        'n_pred_dry':          int(dry_mask.sum()),
    }


# ── Report ─────────────────────────────────────────────────────────
def fmt(v):
    if isinstance(v, float) and not np.isnan(v):
        return f"{v:.4f}"
    return str(v)


def print_side_by_side(new_metrics, old_metrics):
    print("\n" + "═" * 78)
    print("📊  COMPARISON — both models evaluated on identical test set")
    print("═" * 78)
    print(f"   Test set: {TEST_DIR}")
    print(f"   Images  : {new_metrics['n_total']} total")
    print(f"             {(new_metrics['n_total'] - new_metrics['n_pred_dry']):4d} not_dry ground truth")
    print()
    rows = [
        ("Accuracy",                  'accuracy'),
        ("Precision (dry)",           'precision_dry'),
        ("Recall    (dry)",           'recall_dry'),
        ("F1        (dry)",           'f1_dry'),
        ("Precision (macro)",         'precision_macro'),
        ("Recall    (macro)",         'recall_macro'),
        ("F1        (macro)",         'f1_macro'),
        ("AUC (dryness confidence)",  'auc_dryness'),
        ("Mean dryness conf (all)",   'mean_conf_overall'),
        ("Mean dryness conf (pred=dry)", 'mean_conf_when_pred_dry'),
        ("# predicted dry / total",   None),  # custom row below
    ]
    header = f"{'Metric':<36}{'dryness_v2.pth':>20}{'efficientnet_b4_skin.pth':>26}"
    print(header)
    print("─" * len(header))
    for label, key in rows:
        if key is None:
            new_v = f"{new_metrics['n_pred_dry']}/{new_metrics['n_total']}"
            old_v = f"{old_metrics['n_pred_dry']}/{old_metrics['n_total']}"
        else:
            new_v = fmt(new_metrics[key])
            old_v = fmt(old_metrics[key])
        print(f"{label:<36}{new_v:>20}{old_v:>26}")
    print()

    print("Confusion matrices (rows=truth, cols=pred; col0=dry, col1=not_dry)")
    print(f"  dryness_v2.pth:           {new_metrics['confusion_matrix'].tolist()}")
    print(f"  efficientnet_b4_skin.pth: {old_metrics['confusion_matrix'].tolist()}")

    print("═" * 78)


def verdict_and_decision_rule(new_metrics, old_metrics):
    new_acc, old_acc = new_metrics['accuracy'], old_metrics['accuracy']
    new_f1,  old_f1  = new_metrics['f1_dry'],   old_metrics['f1_dry']

    print("\n🏁  VERDICT")
    print(f"   Δ accuracy (v2 − original): {new_acc - old_acc:+.4f}")
    print(f"   Δ f1_dry   (v2 − original): {new_f1  - old_f1:+.4f}")

    if new_acc > old_acc:
        winner = "dryness_v2.pth"
    elif new_acc < old_acc:
        winner = "efficientnet_b4_skin.pth"
    else:
        winner = "TIE"

    print(f"   Winner by accuracy        : {winner}")
    print()
    print("─" * 78)
    print("📜  Decision rule (per request)")
    print("─" * 78)
    if winner == "dryness_v2.pth":
        print("✓ dryness_v2.pth wins → report what improvements are needed,")
        print("  wait for approval. (Pipeline left untouched.)")
    elif winner == "efficientnet_b4_skin.pth":
        print("✓ efficientnet_b4_skin.pth wins → report gap and recommend next step.")
        print("  (Pipeline left untouched.)")
    else:
        print("✓ Tie. (Pipeline left untouched.)")


# ── Main ───────────────────────────────────────────────────────────
def main():
    if not os.path.isdir(TEST_DIR):
        print(f"✗ Test directory not found: {TEST_DIR}", file=sys.stderr)
        sys.exit(2)

    new_path = next((p for p in NEW_PATHS if os.path.isfile(p)), None)
    if new_path is None:
        print(f"✗ Could not find dryness model. Tried: {NEW_PATHS}", file=sys.stderr)
        sys.exit(2)
    if not os.path.isfile(OLD_PATH):
        print(f"✗ Could not find old model: {OLD_PATH}", file=sys.stderr)
        sys.exit(2)

    device = pick_device()
    print(f"🖥  Device: {device}")

    # NEW (binary)
    new_model, new_classes, new_size, new_mean, new_std = \
        load_checkpoint(new_path, "dryness_v2.pth (binary)")
    try:
        new_dryness_idx = [c.lower() for c in new_classes].index('dry')
    except ValueError:
        new_dryness_idx = 0
    print(f"   dryness class index: {new_dryness_idx}")

    # OLD (4-class)
    old_model, old_classes, old_size, old_mean, old_std = \
        load_checkpoint(OLD_PATH, "efficientnet_b4_skin.pth (4-class)")
    try:
        old_dryness_idx = [c.lower() for c in old_classes].index('dryness')
    except ValueError:
        old_dryness_idx = 2
    print(f"   dryness class index: {old_dryness_idx}")

    # Use each model's expected input size & normalisation.
    _, new_loader = make_loader(new_size, new_mean, new_std)
    _, old_loader = make_loader(old_size, old_mean, old_std)

    new_p, new_y, new_c = evaluate(new_model, new_loader, device,
                                    new_classes, new_dryness_idx,
                                    "dryness_v2.pth")
    old_p, old_y, old_c = evaluate(old_model, old_loader, device,
                                    old_classes, old_dryness_idx,
                                    "efficientnet_b4_skin.pth")

    # Sanity: same labels (both loaders read the same folder structure).
    assert np.array_equal(new_y, old_y), "Label mismatch — loaders disagree."

    new_metrics = compute_metrics(new_y, new_p, new_c)
    old_metrics = compute_metrics(old_y, old_p, old_c)

    # Per-class breakdown for context.
    print("\n── Classification report — dryness_v2.pth ──")
    print(classification_report(new_y, new_p, target_names=['dry', 'not_dry'],
                                  digits=4, zero_division=0))
    print("── Classification report — efficientnet_b4_skin.pth ──")
    print(classification_report(old_y, old_p, target_names=['dry', 'not_dry'],
                                  digits=4, zero_division=0))

    print_side_by_side(new_metrics, old_metrics)
    verdict_and_decision_rule(new_metrics, old_metrics)


if __name__ == "__main__":
    main()
