#!/usr/bin/env python3
"""
Run inference with the trained U-Net checkpoint on a few eczema images and
save comparison visualizations to media/visualizations/eczema_predictions/.

Output files:
  media/visualizations/eczema_predictions/<image_name>_compare.png
"""
from pathlib import Path
import torch
import torch.nn as nn
import numpy as np
import cv2
import segmentation_models_pytorch as smp
from PIL import Image
import os

CHECKPOINT = Path('core/models/unet_checkpoints/eczema_pseudo/best_model.pth')
DATA_DIR = Path('data_eczema')
OUT_DIR = Path('media/visualizations/eczema_predictions')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_model(checkpoint_path: Path, device: torch.device):
    model = smp.Unet(
        encoder_name='resnet34',
        encoder_weights='imagenet',
        in_channels=3,
        classes=1,
        activation=None
    )
    model.to(device)
    ck = torch.load(str(checkpoint_path), map_location=device)
    model.load_state_dict(ck['model_state_dict'])
    model.eval()
    return model


def preprocess_image(img_path: Path, image_size=256):
    img = Image.open(img_path).convert('RGB')
    arr = np.array(img)
    img_resized = cv2.resize(arr, (image_size, image_size), interpolation=cv2.INTER_LINEAR)
    tensor = torch.from_numpy(img_resized).permute(2, 0, 1).float() / 255.0
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    tensor = (tensor - mean) / std
    return tensor.unsqueeze(0), img_resized


def postprocess_mask(pred: torch.Tensor):
    # pred: (1,1,H,W) logits -> sigmoid -> binary mask 0/255 uint8
    prob = torch.sigmoid(pred)
    mask = (prob > 0.5).cpu().numpy().astype('uint8')[0, 0] * 255
    return mask


def create_comparison(original_crop, gt_mask, pred_mask):
    # all inputs are HxW or HxWx3
    if gt_mask.ndim == 2:
        gt_disp = cv2.cvtColor(gt_mask, cv2.COLOR_GRAY2RGB)
    else:
        gt_disp = gt_mask
    if pred_mask.ndim == 2:
        pred_disp = cv2.cvtColor(pred_mask, cv2.COLOR_GRAY2RGB)
    else:
        pred_disp = pred_mask
    # Make predicted mask colored overlay on original for nicer view
    overlay = original_crop.copy()
    colored = cv2.applyColorMap(pred_mask, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(overlay, 0.6, colored, 0.4, 0)

    comparison = np.hstack([original_crop, gt_disp, overlay])
    return comparison


def main(n_samples=5):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Device:', device)
    if not CHECKPOINT.exists():
        print('Checkpoint not found:', CHECKPOINT)
        return

    model = load_model(CHECKPOINT, device)

    imgs = sorted((DATA_DIR / 'images').glob('*'))
    masks = sorted((DATA_DIR / 'masks').glob('*'))
    pairs = list(zip(imgs, masks))
    if len(pairs) == 0:
        print('No image-mask pairs found in', DATA_DIR)
        return

    for img_path, mask_path in pairs[:n_samples]:
        tensor, resized = preprocess_image(img_path)
        tensor = tensor.to(device)
        with torch.no_grad():
            pred = model(tensor)
        pred_mask = postprocess_mask(pred)

        gt_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        gt_mask = cv2.resize(gt_mask, (resized.shape[1], resized.shape[0]), interpolation=cv2.INTER_NEAREST)

        comp = create_comparison(resized, gt_mask, pred_mask)
        out_p = OUT_DIR / f"{img_path.stem}_compare.png"
        cv2.imwrite(str(out_p), comp)
        print('Saved', out_p)

    print('Done. Visualizations saved to', OUT_DIR)


if __name__ == '__main__':
    main()
