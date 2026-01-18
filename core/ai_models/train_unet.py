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
        
        # Data augmentation (if enabled)
        if self.augment and np.random.random() > 0.5:
            # Horizontal flip
            image = cv2.flip(image, 1)
            mask = cv2.flip(mask, 1)
        
        # Normalize mask to binary (0 or 1)
        mask_binary = (mask > 127).astype(np.float32)
        
        # Convert to tensors
        # Image: (H, W, C) -> (C, H, W), normalize to [0, 1]
        image_tensor = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        
        # Normalize with ImageNet statistics
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        image_tensor = (image_tensor - mean) / std
        
        # Mask: (H, W) -> (1, H, W)
        mask_tensor = torch.from_numpy(mask_binary).unsqueeze(0).float()
        
        return image_tensor, mask_tensor


def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device
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
        
        # Forward pass
        optimizer.zero_grad()
        outputs = model(images)
        
        # Calculate loss
        loss = criterion(outputs, masks)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
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
                        help='Device for training (cuda or cpu)')
    
    args = parser.parse_args()
    
    # Setup device
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
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
    
    # Initialize model
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights="imagenet",
        in_channels=3,
        classes=1,
        activation=None
    )
    model.to(device)
    
    # Loss function (Dice Loss for class imbalance)
    criterion = DiceLoss()
    
    # Optimizer
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)
    
    # Learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5, verbose=True
    )
    
    # Training loop
    best_val_loss = float('inf')
    
    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch + 1}/{args.epochs}")
        print("-" * 50)
        
        # Train
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        
        # Validate
        val_loss = validate(model, val_loader, criterion, device)
        
        # Update learning rate
        scheduler.step(val_loss)
        
        print(f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            checkpoint_path = os.path.join(args.output_dir, 'best_model.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
            }, checkpoint_path)
            print(f"Saved best model to {checkpoint_path}")
        
        # Save periodic checkpoints
        if (epoch + 1) % 10 == 0:
            checkpoint_path = os.path.join(args.output_dir, f'checkpoint_epoch_{epoch + 1}.pth')
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
