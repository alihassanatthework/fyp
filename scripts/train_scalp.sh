#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Phase 2 — 5-class SCALP classifier training (EfficientNet-B0, 224, MPS)
#
#  Run from the project root:
#    bash scripts/train_scalp.sh                 # full run (~1–3h on Mac GPU)
#    bash scripts/train_scalp.sh --smoke         # 1-epoch tiny smoke test first
#
#  • Trains on dataset/scalp_clean/ (built by scripts/clean_organize_scalp.py).
#  • Saves to core/ai_models/scalp_classifier_v1.pth (won't overwrite existing).
#  • If you hit an MPS out-of-memory error, drop batch:
#      --batch-size 8 --accum-steps 4
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

export PYTORCH_ENABLE_MPS_FALLBACK=1

python - <<'PY'
import torch
ok = torch.backends.mps.is_available()
print(f"🍎 MPS available: {ok} | built: {torch.backends.mps.is_built()} | torch {torch.__version__}")
if not ok:
    raise SystemExit("✗ Mac GPU (MPS) not available — aborting.")
print("✓ Training will run on the Mac GPU (device=mps).")
PY

if [ ! -d "dataset/scalp_clean/train" ]; then
  echo "✗ dataset/scalp_clean/ not found. Build it first:"
  echo "    python scripts/clean_organize_scalp.py --apply"
  exit 1
fi

if [ "$1" == "--smoke" ]; then
  echo "🔬 SMOKE TEST — 1 epoch on a tiny subset (verifies the MPS pipeline)."
  python -u train_scalp_5class.py \
      --device mps --img-size 224 --batch-size 16 --accum-steps 2 \
      --phase1-epochs 1 --phase2-epochs 1 --limit 200 --workers 2 --max-hours 1
  echo "✓ Smoke test done. Run without --smoke for the full training."
  exit 0
fi

python -u train_scalp_5class.py \
    --device mps \
    --img-size 224 \
    --batch-size 16 \
    --accum-steps 2 \
    --phase1-epochs 4 \
    --phase2-epochs 45 \
    --phase1-lr 1e-3 \
    --phase2-lr 1e-4 \
    --weight-decay 1e-4 \
    --label-smoothing 0.1 \
    --mixup-alpha 0.2 \
    --patience 5 \
    --workers 4 \
    --max-hours 4
