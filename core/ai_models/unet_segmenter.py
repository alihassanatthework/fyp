"""
U-Net-based image segmentation module.

This module provides functionality for segmenting skin and scalp regions
to localize conditions using U-Net architecture with ResNet-34 backbone.
"""

import torch
import torch.nn as nn
import numpy as np
from PIL import Image
import cv2
from typing import Tuple, Optional, Union
import segmentation_models_pytorch as smp


class UNetSegmenter:
    """
    U-Net-based segmenter for condition localization.
    
    Uses segmentation-models-pytorch with ResNet-34 backbone
    initialized with ImageNet weights.
    
    Attributes:
        model: Loaded U-Net model
        device: Device for inference (cuda or cpu)
        threshold: Threshold for binary mask (default: 0.5)
    """
    
    def __init__(self, model_path: Optional[str] = None, device: str = 'cpu'):
        """
        Initialize the U-Net segmenter.
        
        Args:
            model_path: Path to pre-trained U-Net model weights (.pth file)
            device: Device for inference ('cuda' or 'cpu')
        """
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.threshold = 0.5
        
        # Initialize U-Net with ResNet-34 backbone and ImageNet weights
        try:
            self.model = smp.Unet(
                encoder_name="resnet34",
                encoder_weights="imagenet",
                in_channels=3,
                classes=1,  # Binary segmentation (healthy vs affected)
                activation=None  # We'll apply sigmoid manually
            )
            
            # Move model to device
            self.model.to(self.device)
            self.model.eval()
            print(f"✅ U-Net model initialized on {self.device}")
        except Exception as e:
            print(f"⚠️ U-Net initialization failed: {e}")
            # Create a dummy model that returns zeros
            import torch.nn as nn
            self.model = None
            self._init_failed = True
        
        # Load weights if provided
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """
        Load U-Net model weights from file.
        
        Args:
            model_path: Path to model weights file (.pth)
        """
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            self.model.eval()
        except Exception as e:
            raise ValueError(f"Failed to load model from {model_path}: {str(e)}")
    
    def segment(self, image: np.ndarray) -> np.ndarray:
        """
        Segment image to produce binary mask.
        
        Args:
            image: Input image as numpy array (256x256x3, RGB, uint8)
            
        Returns:
            Binary segmentation mask (256x256, uint8, 0=healthy, 255=affected)
        """
        # Validate input shape
        if image.shape != (256, 256, 3):
            raise ValueError(f"Input image must be 256x256x3, got {image.shape}")
        
        # If model failed to initialize, return empty mask
        if self.model is None or hasattr(self, '_init_failed'):
            print("⚠️ U-Net model not available, returning empty mask")
            return np.zeros((256, 256), dtype=np.uint8)
        
        try:
            # Preprocess image
            image_tensor = self._preprocess(image)
            
            # Inference
            with torch.no_grad():
                output = self.model(image_tensor)
                
                # Apply sigmoid activation
                output = torch.sigmoid(output)
                
                # Threshold to create binary mask
                binary_mask = (output > self.threshold).float()
                
                # Convert to numpy
                binary_mask_np = binary_mask.squeeze().cpu().numpy()
                
                # Convert to uint8 (0 or 255)
                binary_mask_uint8 = (binary_mask_np * 255).astype(np.uint8)
            
            return binary_mask_uint8
        except Exception as e:
            print(f"⚠️ U-Net segmentation failed: {e}, returning empty mask")
            import traceback
            traceback.print_exc()
            return np.zeros((256, 256), dtype=np.uint8)
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for model input.
        
        Args:
            image: Input image (256x256x3, RGB, uint8)
            
        Returns:
            Preprocessed tensor (1x3x256x256, float32, normalized)
        """
        # Normalize to [0, 1]
        image_float = image.astype(np.float32) / 255.0
        
        # Convert to tensor and add batch dimension
        image_tensor = torch.from_numpy(image_float).permute(2, 0, 1).unsqueeze(0)
        
        # Normalize with ImageNet statistics
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        image_tensor = (image_tensor - mean) / std
        
        return image_tensor.to(self.device)
