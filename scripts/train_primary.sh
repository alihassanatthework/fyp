#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Phase 1 — PRIMARY 4-class EfficientNet-B4 training (380×380, MPS)
#
#  Run from the project root:
#    bash scripts/train_primary.sh
#
#  • Architecture identical to efficientnet_b4_skin.pth (drop-in).
#  • Saves to core/ai_models/efficientnet_b4_primary_v2.pth
#    (does NOT overwrite any existing .pth).
#  • Memory plan for 8–9 GB MPS at 380×380 full fine-tune:
#      batch 8 × accum 4 = effective 32, float16 AMP, channels_last.
#      If you hit an MPS out-of-memory error, drop to:
#        --batch-size 4 --accum-steps 8
# ─────────────────────────────────────────────────────────────────
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
echo "📁 Project: $PROJECT_DIR"

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
  echo "✓ venv activated"
else
  echo "✗ venv not found"; exit 1
fi

# Mac GPU (Apple Metal / MPS): let unsupported ops fall back to CPU
# instead of erroring out mid-training.
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Verify the Mac GPU is actually visible to PyTorch before training.
python - <<'PY'
import torch
ok = torch.backends.mps.is_available()
built = torch.backends.mps.is_built()
print(f"🍎 MPS available: {ok}  |  built: {built}  |  torch {torch.__version__}")
if not ok:
    raise SystemExit("✗ Mac GPU (MPS) not available — aborting. Update macOS/torch.")
print("✓ Training will run on the Mac GPU (device=mps).")
PY

python -u train_primary_4class.py \
    --device mps \
    --img-size 380 \
    --batch-size 8 \
    --accum-steps 4 \
    --amp \
    --phase1-epochs 5 \
    --phase2-epochs 45 \
    --phase1-lr 1e-3 \
    --phase2-lr 1e-4 \
    --weight-decay 1e-4 \
    --label-smoothing 0.1 \
    --mixup-alpha 0.2 \
    --patience 8 \
    --workers 4 \
    --max-hours 6
