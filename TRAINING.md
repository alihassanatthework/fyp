TRAINING & CHECKPOINTS
======================

This document explains how to reproduce the U-Net training (eczema) and how to publish the trained checkpoints so that anyone cloning this repository can fetch them.

1) Reproducible training (quick start)

- Create and activate a Python virtualenv and install dependencies:

  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

- Run training (example using Apple MPS):

  python core/ai_models/train_unet.py \
    --encoder resnet50 \
    --decoder_attention_type scse \
    --freeze_epochs 3 \
    --epochs 30 \
    --device mps

  Adjust flags as needed (e.g. --epochs, --batch_size, --device).

2) Versioning model weights using Git LFS (recommended)

We track the heavy checkpoint files under `core/models/unet_checkpoints/` using Git LFS so they don't bloat the Git history and so that collaborators can pull them easily.

Steps for the machine that will publish the checkpoints:

- Install Git LFS (macOS examples):
  - Homebrew: `brew install git-lfs`
  - Or download from: https://git-lfs.github.com/

- Run the helper script included in this repo (from repo root):

  chmod +x scripts/publish_checkpoints_with_lfs.sh
  ./scripts/publish_checkpoints_with_lfs.sh

This will:
- run `git lfs install` (hooks)
- run `git lfs track` for the `.pth` files
- stage `.gitattributes` and the checkpoint directory
- commit and push to the current branch

Notes and troubleshooting
- If the remote repository does not have Git LFS enabled, pushing LFS objects will fail. On GitHub, LFS is supported for repositories but large storage may incur usage limits.
- If you cloned this repo and want to fetch LFS files, run `git lfs pull` after `git clone` (or `git clone` will fetch LFS objects automatically if Git LFS is installed).
- If you prefer not to use Git LFS, consider uploading your checkpoints to a release, S3 bucket or Google Drive and adding small download scripts (not covered here).
 - If you prefer not to use Git LFS, consider uploading your checkpoints to a release, S3 bucket or Google Drive and adding small download scripts (not covered here).

3) New flags

- `--encoder`: You can now explicitly choose the SMP encoder used inside the U-Net. Example values: `resnet50`, `resnet34`.

  Example: to run training with a ResNet-50 encoder (recommended for transfer learning):

  python core/ai_models/train_unet.py \
    --data_dir data_eczema \
    --output_dir core/models/unet_checkpoints/eczema_resnet50_scse \
    --encoder resnet50 \
    --freeze_epochs 3 \
    --epochs 30 \
    --batch_size 8 \
    --learning_rate 1e-4 \
    --device mps

  (The script will still accept the `UNET_ENCODER` environment variable if you prefer to configure that way.)
