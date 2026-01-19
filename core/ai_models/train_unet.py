"""
Standalone U-Net Training Script.

This script trains a U-Net segmentation model using Dice Loss to address
class imbalance. The training process is completely separate from the
Django inference pipeline.

Usage:
    python train_unet.py --data_dir /path/to/data --epochs 50 --batch_size 8
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import cv2
import os
import argparse
from tqdm import tqdm
import segmentation_models_pytorch as smp
from typing import Tuple, List

# Augmentations
import albumentations as A
from albumentations.pytorch import ToTensorV2
import math


class DiceLoss(nn.Module):
    """
    Dice Loss for binary segmentation.
    
    Addresses class imbalance by focusing on the overlap between
    predicted and ground truth masks.
    """
    
    def __init__(self, smooth: float = 1e-6):
        """
        Initialize Dice Loss.
        
        Args:
            smooth: Smoothing factor to avoid division by zero
        """
        super(DiceLoss, self).__init__()
        self.smooth = smooth
    
    def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Calculate Dice Loss.
        
        Args:
            predictions: Predicted logits (B, 1, H, W)
            targets: Ground truth masks (B, 1, H, W), binary (0 or 1)
            
        Returns:
            Dice loss value
        """
        # Apply sigmoid to predictions
        predictions = torch.sigmoid(predictions)
        
        # Flatten tensors
        predictions_flat = predictions.view(-1)
        targets_flat = targets.view(-1).float()
        
        # Calculate intersection and union
        intersection = (predictions_flat * targets_flat).sum()
        union = predictions_flat.sum() + targets_flat.sum()
        
        # Calculate Dice coefficient
        dice = (2.0 * intersection + self.smooth) / (union + self.smooth)
        
        # Return Dice loss (1 - Dice coefficient)
        return 1.0 - dice


class BCEDiceLoss(nn.Module):
    """
    Combined BCEWithLogits + Dice loss (common for segmentation tasks).
    """
    def __init__(self, smooth: float = 1e-6):
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss()
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # BCE on logits
        bce_loss = self.bce(logits, targets)
        # Dice on probabilities
        probs = torch.sigmoid(logits)
        probs_flat = probs.view(probs.size(0), -1)
        targets_flat = targets.view(targets.size(0), -1)
        intersection = (probs_flat * targets_flat).sum(1)
        dice = (2.0 * intersection + self.smooth) / (probs_flat.sum(1) + targets_flat.sum(1) + self.smooth)
        dice_loss = 1.0 - dice
        return bce_loss + dice_loss.mean()


class SegmentationDataset(Dataset):
    """
    Dataset for U-Net segmentation training.
    
    Expects directory structure:
        data_dir/
            images/
                image1.jpg
                image2.jpg
                ...
            masks/
                image1.png  (binary mask, 0=healthy, 255=affected)
                image2.png
                ...
    """
    
    def __init__(self, data_dir: str, image_size: int = 256, augment: bool = True):
        """
        Initialize dataset.
        
        Args:
            data_dir: Root directory containing 'images' and 'masks' folders
            image_size: Target image size (default: 256)
            augment: Whether to apply data augmentation
        """
        self.data_dir = data_dir
        self.image_size = image_size
        self.augment = augment
        
        # Get list of image files
        images_dir = os.path.join(data_dir, 'images')
        masks_dir = os.path.join(data_dir, 'masks')
        
        if not os.path.exists(images_dir) or not os.path.exists(masks_dir):
            raise ValueError(f"Data directory must contain 'images' and 'masks' folders")
        
        self.image_files = sorted([
            f for f in os.listdir(images_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        
        # Verify corresponding masks exist
        self.valid_pairs = []
        for img_file in self.image_files:
            mask_file = img_file.rsplit('.', 1)[0] + '.png'
            mask_path = os.path.join(masks_dir, mask_file)
            if os.path.exists(mask_path):
                self.valid_pairs.append((img_file, mask_file))
        
        if len(self.valid_pairs) == 0:
            raise ValueError("No valid image-mask pairs found")
        
        print(f"Found {len(self.valid_pairs)} valid image-mask pairs")

        # Build augmentations
        self.train_transform = A.Compose([
            A.HorizontalFlip(p=0.5),
            A.ShiftScaleRotate(shift_limit=0.06, scale_limit=0.15, rotate_limit=20, p=0.5),
            A.OneOf([
                A.GaussNoise(var_limit=(10.0, 50.0), p=0.5),
                A.MedianBlur(blur_limit=3, p=0.5),
            ], p=0.3),
            A.RandomBrightnessContrast(p=0.5),
            A.HueSaturationValue(p=0.3),
            A.ElasticTransform(alpha=1.0, sigma=50, alpha_affine=50, p=0.2),
        ])
        self.val_transform = A.Compose([])
    
    def __len__(self) -> int:
        """Return dataset size."""
        return len(self.valid_pairs)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get image and mask pair.
        
        Args:
            idx: Index of the pair
            
        Returns:
            Tuple of (image_tensor, mask_tensor)
        """
        img_file, mask_file = self.valid_pairs[idx]
        
        # Load image
        img_path = os.path.join(self.data_dir, 'images', img_file)
        image = Image.open(img_path).convert('RGB')
        image = np.array(image)
        
        # Load mask
        mask_path = os.path.join(self.data_dir, 'masks', mask_file)
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        
        # Resize to target size
        image = cv2.resize(image, (self.image_size, self.image_size), interpolation=cv2.INTER_LINEAR)
        mask = cv2.resize(mask, (self.image_size, self.image_size), interpolation=cv2.INTER_NEAREST)
        # Data augmentation (albumentations)
        if self.augment:
            augmented = self.train_transform(image=image, mask=mask)
            image = augmented['image']
            mask = augmented['mask']
        
        # Normalize mask to binary (0 or 1)
        mask_binary = (mask > 127).astype(np.float32)

        # Convert to tensors and normalize using ImageNet stats
        image = image.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406]).reshape(1, 1, 3)
        std = np.array([0.229, 0.224, 0.225]).reshape(1, 1, 3)
        image = (image - mean) / std
        image_tensor = torch.from_numpy(image).permute(2, 0, 1).float()

        # Mask: (H, W) -> (1, H, W)
        mask_tensor = torch.from_numpy(mask_binary).unsqueeze(0).float()

        return image_tensor, mask_tensor


def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    scaler: torch.cuda.amp.GradScaler = None,
    step_scheduler: callable = None,
) -> float:
    """
    Train for one epoch.
    
    Args:
        model: U-Net model
        dataloader: Training data loader
        criterion: Loss function (Dice Loss)
        optimizer: Optimizer
        device: Device for training
        
    Returns:
        Average loss for the epoch
    """
    model.train()
    total_loss = 0.0
    num_batches = 0
    
    for images, masks in tqdm(dataloader, desc="Training"):
        images = images.to(device)
        masks = masks.to(device)

        optimizer.zero_grad()
        if scaler is not None:
            with torch.cuda.amp.autocast():
                outputs = model(images)
                loss = criterion(outputs, masks)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(images)
            loss = criterion(outputs, masks)
            loss.backward()
            optimizer.step()

        # Optionally step per-batch scheduler (OneCycleLR)
        if step_scheduler is not None:
            try:
                step_scheduler.step()
            except Exception:
                pass

        total_loss += loss.item()
        num_batches += 1
    
    return total_loss / num_batches if num_batches > 0 else 0.0


def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> float:
    """
    Validate model.
    
    Args:
        model: U-Net model
        dataloader: Validation data loader
        criterion: Loss function
        device: Device for validation
        
    Returns:
        Average validation loss
    """
    model.eval()
    total_loss = 0.0
    num_batches = 0
    
    with torch.no_grad():
        for images, masks in tqdm(dataloader, desc="Validating"):
            images = images.to(device)
            masks = masks.to(device)

            # Forward pass
            outputs = model(images)

            # Calculate loss
            loss = criterion(outputs, masks)

            total_loss += loss.item()
            num_batches += 1
    
    return total_loss / num_batches if num_batches > 0 else 0.0


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train U-Net segmentation model')
    parser.add_argument('--data_dir', type=str, required=True,
                        help='Directory containing images/ and masks/ folders')
    parser.add_argument('--output_dir', type=str, default='./checkpoints',
                        help='Directory to save model checkpoints')
    parser.add_argument('--epochs', type=int, default=50,
                        help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=8,
                        help='Batch size for training')
    parser.add_argument('--learning_rate', type=float, default=1e-4,
                        help='Learning rate')
    parser.add_argument('--val_split', type=float, default=0.2,
                        help='Validation split ratio')
    parser.add_argument('--device', type=str, default='cuda',
                        help='Device for training (cuda or cpu or mps)')
    parser.add_argument('--freeze_epochs', type=int, default=3,
                        help='Number of initial epochs to freeze encoder weights for faster fine-tuning')
    
    args = parser.parse_args()
    
    # Setup device: prefer CUDA, then Apple MPS, else CPU
    preferred = args.device.lower() if args.device else 'auto'
    if preferred in ('cuda', 'cpu', 'mps'):
        # honor explicit request if possible
        device = torch.device(preferred if preferred != 'auto' else 'cpu')
    else:
        device = None

    if device is None:
        if torch.cuda.is_available():
            device = torch.device('cuda')
        else:
            # Apple Metal Performance Shaders (MPS) for Apple Silicon
            try:
                if getattr(torch.backends, 'mps', None) and torch.backends.mps.is_available():
                    device = torch.device('mps')
                else:
                    device = torch.device('cpu')
            except Exception:
                device = torch.device('cpu')

    print(f"Using device: {device}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create dataset
    full_dataset = SegmentationDataset(args.data_dir, image_size=256, augment=True)
    
    # Split into train and validation
    val_size = int(len(full_dataset) * args.val_split)
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        full_dataset, [train_size, val_size]
    )
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )
    
    # Initialize model (use a stronger encoder for better accuracy)
    # Default to ResNet50 with attention gates for better accuracy & faster fine-tuning
    encoder_name = os.getenv('UNET_ENCODER', 'resnet50')
    try:
        model = smp.Unet(
            encoder_name=encoder_name,
            encoder_weights="imagenet",
            in_channels=3,
            classes=1,
            decoder_attention_type="scse",
            activation=None
        )
        model.to(device)
    except Exception as e:
        print(f"⚠️ Failed to create UNet with encoder {encoder_name}: {e}. Falling back to resnet34 with attention.")
        model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights="imagenet",
            decoder_attention_type="scse",
            in_channels=3,
            classes=1,
            activation=None
        )
        model.to(device)

    # Loss function (BCE + Dice)
    criterion = BCEDiceLoss()

    # Optimizer
    optimizer = optim.AdamW(model.parameters(), lr=args.learning_rate)

    # Scheduler: prefer OneCycleLR when training on GPU for faster convergence
    use_onecycle = device.type == 'cuda'
    if use_onecycle:
        steps_per_epoch = max(1, len(train_loader))
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=args.learning_rate,
            steps_per_epoch=steps_per_epoch,
            epochs=args.epochs,
            pct_start=0.1,
            anneal_strategy='cos',
            div_factor=10.0,
            final_div_factor=100.0,
        )
        per_batch_scheduler = scheduler
    else:
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        per_batch_scheduler = None
    
    # Optionally freeze encoder for a few initial epochs to train decoder faster
    freeze_epochs = int(args.freeze_epochs)
    if freeze_epochs > 0:
        try:
            for name, param in model.encoder.named_parameters():
                param.requires_grad = False
            print(f"🔒 Encoder parameters frozen for first {freeze_epochs} epochs (encoder={encoder_name})")
        except Exception:
            print("⚠️ Could not freeze encoder parameters (unexpected model structure)")

    # Training loop
    best_val_loss = float('inf')

    # Mixed precision scaler (only used if CUDA)
    scaler = torch.cuda.amp.GradScaler() if device.type == 'cuda' else None

    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch + 1}/{args.epochs}")
        print("-" * 50)

        # Unfreeze the encoder after the initial freeze period to fine-tune whole model
        if freeze_epochs > 0 and epoch == freeze_epochs:
            try:
                for name, param in model.encoder.named_parameters():
                    param.requires_grad = True
                print(f"🔓 Encoder unfrozen at epoch {epoch} — full fine-tuning now")
            except Exception:
                print("⚠️ Could not unfreeze encoder parameters (unexpected model structure)")

        # Train (pass scaler and per-batch scheduler when available)
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device, scaler=scaler, step_scheduler=per_batch_scheduler)

        # Validate
        val_loss = validate(model, val_loader, criterion, device)

        # Update learning rate for epoch-level scheduler
        if not use_onecycle:
            try:
                scheduler.step(val_loss)
            except Exception:
                pass

        print(f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            # Save under a distinct name to avoid overwriting baseline checkpoints
            checkpoint_path = os.path.join(args.output_dir, 'resnet_unet_best.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'encoder': encoder_name,
            }, checkpoint_path)
            print(f"Saved best model to {checkpoint_path}")

        # Save periodic checkpoints
        if (epoch + 1) % 10 == 0:
            checkpoint_path = os.path.join(args.output_dir, f'resnet_unet_checkpoint_epoch_{epoch + 1}.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
            }, checkpoint_path)
    
    print("\nTraining completed!")
    print(f"Best validation loss: {best_val_loss:.4f}")


if __name__ == '__main__':
    main()
