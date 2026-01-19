"""Evaluation script for U-Net checkpoints.

Computes Dice and IoU on a given dataset using a trained checkpoint.

Usage:
    python eval_unet.py --data_dir data_eczema --checkpoint core/models/unet_checkpoints/eczema_resnet50_scse/resnet_unet_best.pth --device mps

"""
import argparse
import os
import torch
import numpy as np
from torch.utils.data import DataLoader
from core.ai_models.train_unet import SegmentationDataset
import segmentation_models_pytorch as smp


def dice_score(pred, target, smooth=1e-6):
    pred_flat = pred.reshape(-1)
    target_flat = target.reshape(-1)
    intersection = (pred_flat * target_flat).sum()
    return (2.0 * intersection + smooth) / (pred_flat.sum() + target_flat.sum() + smooth)


def iou_score(pred, target, smooth=1e-6):
    pred_flat = pred.reshape(-1)
    target_flat = target.reshape(-1)
    intersection = (pred_flat * target_flat).sum()
    union = pred_flat.sum() + target_flat.sum() - intersection
    return (intersection + smooth) / (union + smooth)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_dir', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--batch_size', type=int, default=8)
    args = parser.parse_args()

    device = torch.device(args.device if args.device in ('cpu','cuda','mps') else 'cpu')

    # Load dataset
    ds = SegmentationDataset(args.data_dir, image_size=256, augment=False)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False, num_workers=4)

    # Build model (assume resnet50+scse since our checkpoints use that)
    model = smp.Unet(encoder_name='resnet50', encoder_weights=None, in_channels=3, classes=1, decoder_attention_type='scse', activation=None)
    checkpoint = torch.load(args.checkpoint, map_location='cpu')
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()

    dices = []
    ious = []

    with torch.no_grad():
        for imgs, masks in loader:
            imgs = imgs.to(device)
            masks = masks.numpy()
            outputs = model(imgs)
            probs = torch.sigmoid(outputs).cpu().numpy()
            preds = (probs > 0.5).astype(np.float32)
            for p, t in zip(preds, masks):
                dices.append(dice_score(p, t))
                ious.append(iou_score(p, t))

    print(f"Mean Dice: {np.mean(dices):.4f}, Mean IoU: {np.mean(ious):.4f}")


if __name__ == '__main__':
    main()
