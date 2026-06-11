#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Dryness model training — one-shot runner
#
#  Run from the project root:
#    bash scripts/train_dryness.sh
#
#  Pipeline:
#    1. Activate venv
#    2. Download + organise the Kaggle dataset (idempotent)
#    3. Train EfficientNet-B4 binary dry/not_dry on Mac GPU (MPS)
#    4. Save best weights → core/ai_models/dryness_v2.pth
#       (does NOT touch the existing efficientnet_b4_skin.pth)
#
#  Memory plan (8 GB MPS):
#    Image size 224, per-step batch 16, gradient accumulation 2
#    → effective batch 32  ·  peak ~7.5 GB MPS (safe under 9 GB cap)
#
#  Spec compliance:
#    Phase 1: 5 epochs, classifier head only, lr 1e-3
#    Phase 2: up to 45 epochs, full fine-tune, lr 1e-4 + cosine + warmup
#    Optimizer: AdamW (weight_decay 1e-4)
#    Loss:      CE label-smoothing 0.1 (no double-weighting; sampler handles imbalance)
#    Augment:   flip, rot ±15°, brightness/contrast ±0.2, GaussianBlur, MixUp α=0.2
#    Early stopping: patience 10 on val accuracy
#    Total cap: 50 epochs
# ─────────────────────────────────────────────────────────────────

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
echo "📁 Project: $PROJECT_DIR"

if [ -f "venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
  echo "✓ venv activated"
else
  echo "✗ venv not found at $PROJECT_DIR/venv — create it first."
  exit 1
fi

echo ""
echo "── Step 1/2 — Download + prepare dataset ──"
python scripts/download_dryness_dataset.py

echo ""
echo "── Step 2/2 — Train EfficientNet-B4 dryness model on MPS ──"
python -u train_dryness_v2.py \
    --device mps \
    --img-size 224 \
    --batch-size 16 \
    --accum-steps 2 \
    --phase1-epochs 5 \
    --phase2-epochs 45 \
    --phase1-lr 1e-3 \
    --phase2-lr 1e-4 \
    --weight-decay 1e-4 \
    --label-smoothing 0.1 \
    --mixup-alpha 0.2 \
    --rebalance sampler \
    --patience 10 \
    --workers 0
