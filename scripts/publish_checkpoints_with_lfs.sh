#!/usr/bin/env bash
set -euo pipefail

# Helper to track and push checkpoints using Git LFS.
# Run this AFTER installing git-lfs on your machine.

BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $BRANCH"

echo "Installing git-lfs hooks (if not already installed)..."
git lfs install

echo "Tracking .pth files under core/models/unet_checkpoints..."
git lfs track "core/models/unet_checkpoints/**/*.pth"

echo "Staging .gitattributes and checkpoint files..."
git add .gitattributes
git add core/models/unet_checkpoints/

echo "Committing and pushing (will upload via LFS)..."
git commit -m "Add model checkpoints (tracked by Git LFS)" || echo "No changes to commit"
git push origin "$BRANCH"

echo "Done. Large files are tracked by Git LFS and pushed." 
